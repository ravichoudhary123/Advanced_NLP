import Foundation

@MainActor
final class TTSQueueService: ObservableObject {
    @Published private(set) var activeJobs: [TTSJob] = []

    private let repository: AudiobookRepository
    private let engineManager: TTSEngineManager
    private let parser = DefaultTextParser()

    init(repository: AudiobookRepository, engineManager: TTSEngineManager) {
        self.repository = repository
        self.engineManager = engineManager
    }

    func enqueueGeneration(for book: Audiobook, voice: VoiceProfile, chunkSize: Int) async {
        book.status = .queued
        try? repository.saveBook(book)

        for chapter in book.chapters.sorted(by: { $0.index < $1.index }) {
            let chunks = parser.chunk(chapterText: chapter.rawText, targetSize: chunkSize)
            chapter.segments = chunks.map {
                AudioSegment(index: $0.index, textRangeStart: $0.start, textRangeEnd: $0.end, sourceText: $0.text, status: .queued)
            }
            chapter.status = .queued
        }

        try? repository.saveBook(book)

        for chapter in book.chapters.sorted(by: { $0.index < $1.index }) {
            chapter.status = .generating
            for segment in chapter.segments.sorted(by: { $0.index < $1.index }) {
                await runJob(book: book, chapter: chapter, segment: segment, voice: voice)
            }
            chapter.status = chapter.segments.allSatisfy { $0.status == .completed } ? .completed : .failed
            try? repository.saveBook(book)
        }

        book.status = book.chapters.allSatisfy { $0.status == .completed } ? .completed : .failed
        try? repository.saveBook(book)
    }

    func resumePendingJobs() async {
        // MVP behavior: queue state is persisted in chapters/segments; this hook can resume unfinished jobs on launch.
    }

    private func runJob(book: Audiobook, chapter: Chapter, segment: AudioSegment, voice: VoiceProfile) async {
        var job = TTSJob(id: UUID(), bookID: book.id, chapterID: chapter.id, segmentID: segment.id, status: .running)
        activeJobs.append(job)
        segment.status = .generating

        do {
            let outputURL = try FileStore.audioURL(for: book.id, chapterID: chapter.id, segmentID: segment.id)
            let duration = try await engineManager.selectedEngine.synthesize(text: segment.sourceText, voice: voice, outputURL: outputURL)
            segment.audioFilePath = outputURL.path
            segment.durationSeconds = duration
            segment.status = .completed
            job.status = .completed
        } catch {
            segment.status = .failed
            job.status = .failed(error.localizedDescription)
            book.lastError = error.localizedDescription
        }

        activeJobs.removeAll { $0.id == job.id }
        try? repository.saveBook(book)
    }
}

enum FileStore {
    static func audioURL(for bookID: UUID, chapterID: UUID, segmentID: UUID) throws -> URL {
        let folder = try baseAudioDirectory().appending(path: bookID.uuidString).appending(path: chapterID.uuidString, directoryHint: .isDirectory)
        try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
        return folder.appending(path: "\(segmentID.uuidString).wav")
    }

    static func baseAudioDirectory() throws -> URL {
        let docs = try FileManager.default.url(for: .documentDirectory, in: .userDomainMask, appropriateFor: nil, create: true)
        return docs.appending(path: "GeneratedAudio", directoryHint: .isDirectory)
    }
}

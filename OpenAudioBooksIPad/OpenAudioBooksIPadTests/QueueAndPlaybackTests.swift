import XCTest
@testable import OpenAudioBooksIPad

@MainActor
final class QueueAndPlaybackTests: XCTestCase {
    func testQueueCompletesSegmentStates() async {
        let repo = InMemoryRepo()
        let manager = TTSEngineManager(defaultEngine: MockTTSEngine())
        let queue = TTSQueueService(repository: repo, engineManager: manager)

        let chapter = Chapter(index: 0, title: "Chapter 1", rawText: "hello world")
        let book = Audiobook(title: "B", sourceType: .pasted, chapters: [chapter])
        chapter.book = book

        await queue.enqueueGeneration(for: book, voice: manager.selectedEngine.availableVoices[0], chunkSize: 20)
        XCTAssertEqual(book.status, .completed)
        XCTAssertTrue(book.chapters.first?.segments.allSatisfy { $0.status == .completed } ?? false)
    }

    func testPlaybackPersistenceWritesState() throws {
        let repo = InMemoryRepo()
        let playback = DefaultPlaybackService(repository: repo)
        let book = Audiobook(title: "B", sourceType: .pasted)
        Task { try? await playback.load(book: book, chapter: nil, segment: nil) }
        try playback.persistProgress()

        XCTAssertNotNil(try repo.playbackState(for: book))
    }
}

@MainActor
private final class InMemoryRepo: AudiobookRepository {
    var books: [UUID: Audiobook] = [:]
    var states: [UUID: PlaybackState] = [:]

    func fetchBooks(search: String?) throws -> [Audiobook] { Array(books.values) }
    func fetchBook(id: UUID) throws -> Audiobook? { books[id] }
    func saveBook(_ book: Audiobook) throws { books[book.id] = book }

    func savePlayback(_ state: PlaybackState, for book: Audiobook) throws {
        states[book.id] = state
    }

    func playbackState(for book: Audiobook) throws -> PlaybackState? {
        states[book.id]
    }
}

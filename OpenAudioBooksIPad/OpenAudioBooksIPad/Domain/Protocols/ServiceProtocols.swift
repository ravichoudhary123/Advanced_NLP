import Foundation

protocol AudiobookRepository {
    func fetchBooks(search: String?) throws -> [Audiobook]
    func fetchBook(id: UUID) throws -> Audiobook?
    func saveBook(_ book: Audiobook) throws
    func savePlayback(_ state: PlaybackState, for book: Audiobook) throws
    func playbackState(for book: Audiobook) throws -> PlaybackState?
}

protocol SettingsRepository {
    func load() throws -> AppSettings
    func save(_ settings: AppSettings) throws
}

protocol ImportService {
    func importText(_ text: String, suggestedTitle: String) throws -> Audiobook
    func importFile(at url: URL) throws -> Audiobook
}

protocol TextToSpeechEngine {
    var id: String { get }
    var displayName: String { get }
    var availableVoices: [VoiceProfile] { get }
    func synthesize(text: String, voice: VoiceProfile, outputURL: URL) async throws -> TimeInterval
}

protocol PlaybackService: AnyObject {
    var isPlaying: Bool { get }
    var currentTime: TimeInterval { get }
    var duration: TimeInterval { get }

    func load(book: Audiobook, chapter: Chapter?, segment: AudioSegment?) async throws
    func play()
    func pause()
    func seek(by delta: TimeInterval)
    func setRate(_ rate: Float)
    func persistProgress() throws
}

protocol EPUBImportService {
    func importEPUB(at url: URL) throws -> Audiobook
}

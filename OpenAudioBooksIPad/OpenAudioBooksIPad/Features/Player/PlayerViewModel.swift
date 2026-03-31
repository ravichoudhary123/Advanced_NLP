import Foundation

@MainActor
final class PlayerViewModel: ObservableObject {
    @Published var isPlayerPresented = false
    @Published var selectedBook: Audiobook?
    @Published var currentChapter: Chapter?
    @Published var currentSegment: AudioSegment?
    @Published var rate: Float = 1.0

    private let playbackService: PlaybackService
    private let repository: AudiobookRepository

    init(playbackService: PlaybackService, repository: AudiobookRepository) {
        self.playbackService = playbackService
        self.repository = repository
    }

    func present(book: Audiobook) {
        selectedBook = book
        currentChapter = book.chapters.sorted(by: { $0.index < $1.index }).first
        currentSegment = currentChapter?.segments.sorted(by: { $0.index < $1.index }).first
        isPlayerPresented = true

        Task { try? await playbackService.load(book: book, chapter: currentChapter, segment: currentSegment) }
    }

    func playPause() {
        if playbackService.isPlaying {
            playbackService.pause()
            try? playbackService.persistProgress()
        } else {
            playbackService.play()
        }
    }

    func seek(seconds: TimeInterval) {
        playbackService.seek(by: seconds)
        try? playbackService.persistProgress()
    }

    func updateRate(_ newRate: Float) {
        rate = newRate
        playbackService.setRate(newRate)
    }
}

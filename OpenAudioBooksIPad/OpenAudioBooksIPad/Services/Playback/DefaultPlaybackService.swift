import Foundation
import AVFoundation

@MainActor
final class DefaultPlaybackService: NSObject, PlaybackService {
    private(set) var isPlaying: Bool = false
    private(set) var currentTime: TimeInterval = 0
    private(set) var duration: TimeInterval = 1

    private let repository: AudiobookRepository
    private var player: AVPlayer?
    private var currentBook: Audiobook?
    private var currentSegment: AudioSegment?

    init(repository: AudiobookRepository) {
        self.repository = repository
        super.init()
        configureAudioSession()
    }

    func load(book: Audiobook, chapter: Chapter?, segment: AudioSegment?) async throws {
        currentBook = book
        guard let segment,
              let path = segment.audioFilePath else {
            return
        }

        currentSegment = segment
        let url = URL(fileURLWithPath: path)
        player = AVPlayer(url: url)

        if let saved = try repository.playbackState(for: book) {
            let time = CMTime(seconds: saved.progressSeconds, preferredTimescale: 600)
            player?.seek(to: time)
            setRate(Float(saved.playbackRate))
        }
    }

    func play() {
        player?.play()
        isPlaying = true
    }

    func pause() {
        player?.pause()
        isPlaying = false
    }

    func seek(by delta: TimeInterval) {
        guard let player else { return }
        let updated = max(0, player.currentTime().seconds + delta)
        player.seek(to: CMTime(seconds: updated, preferredTimescale: 600))
        currentTime = updated
    }

    func setRate(_ rate: Float) {
        player?.rate = rate
    }

    func persistProgress() throws {
        guard let book = currentBook else { return }
        let state = try repository.playbackState(for: book) ?? PlaybackState()
        state.progressSeconds = player?.currentTime().seconds ?? currentTime
        state.playbackRate = Double(player?.rate ?? 1.0)
        state.chapterID = currentSegment?.chapter?.id
        state.segmentID = currentSegment?.id
        try repository.savePlayback(state, for: book)
    }

    private func configureAudioSession() {
        do {
            try AVAudioSession.sharedInstance().setCategory(.playback, mode: .spokenAudio, options: [.allowAirPlay])
            try AVAudioSession.sharedInstance().setActive(true)
        } catch {
            print("Audio session setup failed: \(error)")
        }
    }
}

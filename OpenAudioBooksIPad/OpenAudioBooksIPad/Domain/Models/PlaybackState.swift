import Foundation
import SwiftData

@Model
final class PlaybackState {
    @Attribute(.unique) var id: UUID
    var book: Audiobook?
    var chapterID: UUID?
    var segmentID: UUID?
    var progressSeconds: Double
    var playbackRate: Double
    var updatedAt: Date

    init(
        id: UUID = UUID(),
        chapterID: UUID? = nil,
        segmentID: UUID? = nil,
        progressSeconds: Double = 0,
        playbackRate: Double = 1.0,
        updatedAt: Date = .now
    ) {
        self.id = id
        self.chapterID = chapterID
        self.segmentID = segmentID
        self.progressSeconds = progressSeconds
        self.playbackRate = playbackRate
        self.updatedAt = updatedAt
    }
}

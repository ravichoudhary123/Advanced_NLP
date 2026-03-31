import Foundation
import SwiftData

@Model
final class Chapter {
    @Attribute(.unique) var id: UUID
    var book: Audiobook?
    var index: Int
    var title: String
    var rawText: String
    var createdAt: Date
    var updatedAt: Date
    var statusRaw: String

    @Relationship(deleteRule: .cascade, inverse: \AudioSegment.chapter) var segments: [AudioSegment]

    init(
        id: UUID = UUID(),
        index: Int,
        title: String,
        rawText: String,
        status: GenerationStatus = .notStarted,
        createdAt: Date = .now,
        updatedAt: Date = .now,
        segments: [AudioSegment] = []
    ) {
        self.id = id
        self.index = index
        self.title = title
        self.rawText = rawText
        self.statusRaw = status.rawValue
        self.createdAt = createdAt
        self.updatedAt = updatedAt
        self.segments = segments
    }

    var status: GenerationStatus {
        get { GenerationStatus(rawValue: statusRaw) ?? .notStarted }
        set { statusRaw = newValue.rawValue }
    }
}

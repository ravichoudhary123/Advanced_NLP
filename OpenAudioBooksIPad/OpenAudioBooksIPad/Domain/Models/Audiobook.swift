import Foundation
import SwiftData

enum AudiobookSourceType: String, Codable, CaseIterable {
    case txt
    case pdf
    case epub
    case pasted
}

enum GenerationStatus: String, Codable, CaseIterable {
    case notStarted
    case queued
    case generating
    case completed
    case failed
}

@Model
final class Audiobook {
    @Attribute(.unique) var id: UUID
    var title: String
    var author: String?
    var sourceTypeRaw: String
    var sourceFileName: String?
    var createdAt: Date
    var updatedAt: Date
    var statusRaw: String
    var lastError: String?

    @Relationship(deleteRule: .cascade, inverse: \Chapter.book) var chapters: [Chapter]
    @Relationship(deleteRule: .cascade, inverse: \PlaybackState.book) var playbackStates: [PlaybackState]

    init(
        id: UUID = UUID(),
        title: String,
        author: String? = nil,
        sourceType: AudiobookSourceType,
        sourceFileName: String? = nil,
        createdAt: Date = .now,
        updatedAt: Date = .now,
        status: GenerationStatus = .notStarted,
        chapters: [Chapter] = []
    ) {
        self.id = id
        self.title = title
        self.author = author
        self.sourceTypeRaw = sourceType.rawValue
        self.sourceFileName = sourceFileName
        self.createdAt = createdAt
        self.updatedAt = updatedAt
        self.statusRaw = status.rawValue
        self.chapters = chapters
        self.playbackStates = []
    }

    var sourceType: AudiobookSourceType { AudiobookSourceType(rawValue: sourceTypeRaw) ?? .txt }
    var status: GenerationStatus {
        get { GenerationStatus(rawValue: statusRaw) ?? .notStarted }
        set { statusRaw = newValue.rawValue }
    }
}

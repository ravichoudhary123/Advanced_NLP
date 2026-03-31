import Foundation
import SwiftData

@Model
final class AudioSegment {
    @Attribute(.unique) var id: UUID
    var chapter: Chapter?
    var index: Int
    var textRangeStart: Int
    var textRangeEnd: Int
    var sourceText: String
    var audioFilePath: String?
    var durationSeconds: Double?
    var statusRaw: String
    var createdAt: Date

    init(
        id: UUID = UUID(),
        index: Int,
        textRangeStart: Int,
        textRangeEnd: Int,
        sourceText: String,
        audioFilePath: String? = nil,
        durationSeconds: Double? = nil,
        status: GenerationStatus = .notStarted,
        createdAt: Date = .now
    ) {
        self.id = id
        self.index = index
        self.textRangeStart = textRangeStart
        self.textRangeEnd = textRangeEnd
        self.sourceText = sourceText
        self.audioFilePath = audioFilePath
        self.durationSeconds = durationSeconds
        self.statusRaw = status.rawValue
        self.createdAt = createdAt
    }

    var status: GenerationStatus {
        get { GenerationStatus(rawValue: statusRaw) ?? .notStarted }
        set { statusRaw = newValue.rawValue }
    }
}

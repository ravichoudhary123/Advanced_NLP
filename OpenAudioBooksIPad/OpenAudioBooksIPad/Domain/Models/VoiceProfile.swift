import Foundation

struct VoiceProfile: Codable, Hashable, Identifiable {
    let id: String
    let displayName: String
    let locale: String
    let modelID: String
}

struct TTSJob: Identifiable, Hashable {
    enum Status {
        case queued
        case running
        case completed
        case failed(String)
    }

    let id: UUID
    let bookID: UUID
    let chapterID: UUID
    let segmentID: UUID
    var status: Status
}

import Foundation
import SwiftData

@Model
final class AppSettings {
    @Attribute(.unique) var id: UUID
    var selectedEngineID: String
    var selectedVoiceID: String
    var speechRate: Double
    var chunkSize: Int
    var enableNetworkTTS: Bool
    var maxConcurrentJobs: Int

    init(
        id: UUID = UUID(),
        selectedEngineID: String = "mock",
        selectedVoiceID: String = "mock.en.default",
        speechRate: Double = 1.0,
        chunkSize: Int = 900,
        enableNetworkTTS: Bool = false,
        maxConcurrentJobs: Int = 1
    ) {
        self.id = id
        self.selectedEngineID = selectedEngineID
        self.selectedVoiceID = selectedVoiceID
        self.speechRate = speechRate
        self.chunkSize = chunkSize
        self.enableNetworkTTS = enableNetworkTTS
        self.maxConcurrentJobs = maxConcurrentJobs
    }
}

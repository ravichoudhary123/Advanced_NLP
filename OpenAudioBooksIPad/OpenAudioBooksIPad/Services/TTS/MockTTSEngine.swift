import Foundation
import AVFoundation

struct MockTTSEngine: TextToSpeechEngine {
    let id = "mock"
    let displayName = "Mock (AVSpeechSynthesizer)"
    let availableVoices: [VoiceProfile] = [
        VoiceProfile(id: "mock.en.default", displayName: "Default English", locale: "en-US", modelID: "avspeech")
    ]

    func synthesize(text: String, voice: VoiceProfile, outputURL: URL) async throws -> TimeInterval {
        // MVP fallback writes source text as sidecar marker and returns synthetic duration.
        // A real engine should write actual audio bytes to outputURL.
        try text.write(to: outputURL, atomically: true, encoding: .utf8)
        let estimated = max(2.0, Double(text.count) / 14.0)
        try await Task.sleep(for: .milliseconds(120))
        return estimated
    }
}

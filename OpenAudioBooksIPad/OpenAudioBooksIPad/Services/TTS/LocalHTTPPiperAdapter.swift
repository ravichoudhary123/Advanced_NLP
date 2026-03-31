import Foundation

struct LocalHTTPPiperAdapter: TextToSpeechEngine {
    let id = "local-http-piper"
    let displayName = "Piper via Local HTTP"
    let availableVoices: [VoiceProfile] = [
        VoiceProfile(id: "piper.en_US-lessac-medium", displayName: "Lessac Medium", locale: "en-US", modelID: "en_US-lessac-medium")
    ]

    var baseURL: URL = URL(string: "http://127.0.0.1:5002")!

    func synthesize(text: String, voice: VoiceProfile, outputURL: URL) async throws -> TimeInterval {
        var request = URLRequest(url: baseURL.appending(path: "synthesize"))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let payload: [String: Any] = [
            "text": text,
            "voice": voice.modelID
        ]
        request.httpBody = try JSONSerialization.data(withJSONObject: payload)

        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw NSError(domain: "PiperAdapter", code: 1, userInfo: [NSLocalizedDescriptionKey: "Local Piper service error"])
        }

        try data.write(to: outputURL)
        return max(2.0, Double(text.count) / 13.0)
    }
}

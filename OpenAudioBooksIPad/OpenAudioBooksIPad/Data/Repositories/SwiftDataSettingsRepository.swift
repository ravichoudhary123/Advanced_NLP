import Foundation
import SwiftData

@MainActor
final class SwiftDataSettingsRepository: SettingsRepository {
    private let context: ModelContext

    init(context: ModelContext) {
        self.context = context
    }

    func load() throws -> AppSettings {
        if let existing = try context.fetch(FetchDescriptor<AppSettings>()).first {
            return existing
        }

        let defaults = AppSettings()
        context.insert(defaults)
        try context.save()
        return defaults
    }

    func save(_ settings: AppSettings) throws {
        context.insert(settings)
        try context.save()
    }
}

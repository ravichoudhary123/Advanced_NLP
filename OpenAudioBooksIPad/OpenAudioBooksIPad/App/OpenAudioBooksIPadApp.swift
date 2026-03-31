import SwiftUI
import SwiftData

@main
struct OpenAudioBooksIPadApp: App {
    @State private var dependencies = AppDependencies.makeDefault()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(dependencies.container)
                .environmentObject(dependencies.libraryViewModel)
                .environmentObject(dependencies.playerViewModel)
                .environmentObject(dependencies.settingsViewModel)
                .task {
                    await dependencies.bootstrapIfNeeded()
                }
        }
        .modelContainer(dependencies.modelContainer)
    }
}

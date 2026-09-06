import Foundation

struct BridgeConfiguration: Codable, Equatable {
    let baseURL: URL
    let deviceBindingID: UUID
    let consentIDs: [String: UUID]
}

final class ConsentStore {
    private let defaults: UserDefaults
    private let configurationKey = "fitcrew.bridge.configuration"
    private let lastSyncKey = "fitcrew.bridge.last-sync"
    private let studyStartKey = "fitcrew.bridge.study-start"
    private let lastFullReconciliationKey = "fitcrew.bridge.last-full-reconciliation"
    private let identityRevisionKey = "fitcrew.bridge.identity-revision"

    var identityRevision: UUID {
        if let text = defaults.string(forKey: identityRevisionKey), let revision = UUID(uuidString: text) { return revision }
        let revision = UUID()
        defaults.set(revision.uuidString, forKey: identityRevisionKey)
        return revision
    }

    private func rotateIdentityRevision() { defaults.set(UUID().uuidString, forKey: identityRevisionKey) }

    init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
    }

    var configuration: BridgeConfiguration? {
        get {
            guard let data = defaults.data(forKey: configurationKey) else { return nil }
            return try? JSONDecoder().decode(BridgeConfiguration.self, from: data)
        }
        set {
            if configuration?.deviceBindingID != newValue?.deviceBindingID || configuration?.baseURL != newValue?.baseURL {
                rotateIdentityRevision()
            }
            defaults.set(try? JSONEncoder().encode(newValue), forKey: configurationKey)
        }
    }

    func replaceConfiguration(_ newConfiguration: BridgeConfiguration, startedAt: Date = Date()) {
        let deviceChanged = configuration?.deviceBindingID != newConfiguration.deviceBindingID
        configuration = newConfiguration
        // A new login also invalidates requests for the same device binding.
        rotateIdentityRevision()
        if deviceChanged {
            lastSync = nil
            lastFullReconciliation = nil
            studyStart = startedAt
        } else if studyStart == nil {
            studyStart = startedAt
        }
    }

    var lastSync: Date? {
        get { defaults.object(forKey: lastSyncKey) as? Date }
        set { defaults.set(newValue, forKey: lastSyncKey) }
    }

    var studyStart: Date? {
        get { defaults.object(forKey: studyStartKey) as? Date }
        set { defaults.set(newValue, forKey: studyStartKey) }
    }

    var lastFullReconciliation: Date? {
        get { defaults.object(forKey: lastFullReconciliationKey) as? Date }
        set { defaults.set(newValue, forKey: lastFullReconciliationKey) }
    }
}

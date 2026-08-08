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

    init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
    }

    var configuration: BridgeConfiguration? {
        get {
            guard let data = defaults.data(forKey: configurationKey) else { return nil }
            return try? JSONDecoder().decode(BridgeConfiguration.self, from: data)
        }
        set {
            defaults.set(try? JSONEncoder().encode(newValue), forKey: configurationKey)
        }
    }

    func replaceConfiguration(_ newConfiguration: BridgeConfiguration, startedAt: Date = Date()) {
        let deviceChanged = configuration?.deviceBindingID != newConfiguration.deviceBindingID
        configuration = newConfiguration
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

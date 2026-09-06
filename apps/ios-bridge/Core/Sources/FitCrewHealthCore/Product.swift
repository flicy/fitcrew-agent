import Foundation

public struct ProductState: Decodable, Sendable {
    public let journey: ProductJourney?
    public let experiments: [ProductExperiment]
    public let logs: [ProductLog]
    public let mission: ProductMission?
    public let health: ProductHealth
    public let privacyVersion: String

    public static func decode(_ data: Data) throws -> ProductState {
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return try decoder.decode(Self.self, from: data)
    }
}

public struct ProductJourney: Decodable, Sendable {
    public let id, goal, title, startDate: String
    public let days, revision: Int
}

public struct ProductHealth: Decodable, Sendable {
    public let sampleCount: Int
    public let lastSyncAt: String?
}

public struct ProductMission: Decodable, Sendable {
    public let id, title, status, date, why: String
    public let revision: Int
}

public enum JSONValue: Decodable, Sendable {
    case string(String), number(Double), bool(Bool), array([JSONValue]), object([String: JSONValue]), null
    public init(from decoder: Decoder) throws {
        let c = try decoder.singleValueContainer()
        if c.decodeNil() { self = .null }
        else if let v = try? c.decode(String.self) { self = .string(v) }
        else if let v = try? c.decode(Bool.self) { self = .bool(v) }
        else if let v = try? c.decode(Double.self) { self = .number(v) }
        else if let v = try? c.decode([JSONValue].self) { self = .array(v) }
        else { self = .object(try c.decode([String: JSONValue].self)) }
    }
    public var display: String {
        switch self {
        case .string(let v): return v
        case .number(let v): return v.formatted()
        case .bool(let v): return v ? "是" : "否"
        case .array(let v): return v.map(\.display).joined(separator: "、")
        case .object(let v): return v.sorted { $0.key < $1.key }.map { "\($0.key)：\($0.value.display)" }.joined(separator: "\n")
        case .null: return "暂无"
        }
    }
}

public struct ProductExperiment: Decodable, Identifiable, Sendable {
    public let id, title, hypothesis, intervention, status, source: String
    public let metrics, successCriteria, stopConditions, dataCategories: [String]
    public let durationDays, revision: Int
    public let result: JSONValue?
    public var actions: [String] {
        switch status {
        case "proposed": return ["accept"]
        case "active", "running", "accepted": return ["pause", "stop", "evaluate"]
        case "paused": return ["resume", "stop"]
        default: return []
        }
    }
}

public struct ProductLog: Decodable, Identifiable, Sendable {
    public let id, feeling, note, createdAt: String
    public let energy, stress, revision: Int
}

public enum BodyCheckInput {
    public static func isValid(energy: Int, stress: Int, note: String) -> Bool {
        (1...5).contains(energy) && (1...3).contains(stress) && note.count <= 500
    }
}

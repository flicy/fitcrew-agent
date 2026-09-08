import Foundation

public struct ProductState: Decodable, Sendable {
    public let journey: ProductJourney?
    public let journeyProgress: ProductJourneyProgress?
    public let milestones: [ProductMilestone]?
    public let experiments: [ProductExperiment]
    public let logs: [ProductLog]
    public let mission: ProductMission?
    public let health: ProductHealth
    public let privacyVersion: String
    public let trends: ProductTrends?
    public let healthTrends: ProductHealthTrends?
    public let nextCheck: ProductNextCheck?
    public let onboarding: ProductOnboarding?
    public let todayContext: ProductTodayContext?
    public let confirmedMemories: [ProductConfirmedMemory]?

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
    public let adjustedAt: String?
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
    public let purpose, baselineStart, acceptedAt, endsAt: String?
    public let result: JSONValue?
    public let userFeedback: ProductFeedback?
    public var canGiveFeedback: Bool {
        guard status == "completed", case .object(let fields) = result,
              case .string(let resultStatus) = fields["status"] else { return false }
        return resultStatus == "descriptive_only" || resultStatus == "insufficient_data"
    }
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
    public let sleepFeeling, trainingFeeling, stressSource: String?
}

public enum BodyCheckInput {
    public static func isValid(energy: Int, stress: Int, note: String) -> Bool {
        (1...5).contains(energy) && (1...3).contains(stress) && note.count <= 500
    }
}

public struct ProductTrends: Decodable, Sendable {
    public let source, windowEnd: String
    public let points: [ProductTrendPoint]
}

public struct ProductTrendPoint: Decodable, Identifiable, Sendable, Equatable {
    public var id: String { date }
    public let date: String
    public let count: Int
    public let energy, stress: Double?
    public let events: [String]?
}

public struct ProductNextCheck: Decodable, Sendable {
    public let title, detail, action: String
}

public struct ProductOnboarding: Decodable, Sendable {
    public let step, revision: Int
    public let route: String?
}

public struct ProductTodayContext: Decodable, Sendable {
    public let status, title, detail, windowStart, windowEnd, source: String
    public let observedDays: Int
    public let healthCategories: [String]
}

public struct ProductFeedback: Decodable, Sendable {
    public let assessment: String
    public let memoryConfirmed: Bool
}
public struct ProductConfirmedMemory: Decodable, Identifiable, Sendable {
    public let id, text, experimentTitle, confirmedAt, notice: String
}

public struct ProductJourneyProgress: Decodable, Sendable {
    public let day, totalDays, phase, observedDays, missingDays: Int
    public let title, windowEnd, notice: String
}

public struct ProductMilestone: Decodable, Identifiable, Sendable {
    public let id, date, status, title, evidence: String
    public let action: String?
}

public struct ProductHealthTrends: Decodable, Sendable {
    public let timezone, windowEnd, notice: String
    public let points: [ProductHealthPoint]
}
public struct ProductHealthPoint: Decodable, Identifiable, Sendable, Equatable {
    public var id: String { date }
    public let date: String
    public let metrics: [String: ProductHealthMetric]
}
public struct ProductHealthMetric: Decodable, Sendable, Equatable {
    public let value: Double?
    public let unit, status: String
    public let sampleCount: Int
    public let sources: [String]
    public var displayValue: Double? { status == "partial" && value?.isFinite == true ? value : nil }
    public var statusLabel: String {
        switch status {
        case "partial": return "部分样本"
        case "missing": return "无样本"
        case "not_authorized": return "未授权"
        case "source_conflict": return "来源冲突"
        case "invalid": return "数据异常"
        default: return "待核实"
        }
    }
}

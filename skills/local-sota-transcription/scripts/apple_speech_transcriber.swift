import AVFoundation
import Foundation
import Speech

struct Segment: Codable {
    let start: Double
    let end: Double
    let text: String
}

struct TranscriptionPayload: Codable {
    let engine: String
    let locale: String
    let segments: [Segment]
    let text: String
}

struct SupportPayload: Codable {
    let available: Bool
    let locale: String
    let supported: Bool
    let installed: Bool
}

enum CLIError: Error, CustomStringConvertible {
    case usage
    case unavailable
    case unsupportedLocale(String)
    case uninstalledLocale(String)
    case missingTimeRange
    case emptyTranscript

    var description: String {
        switch self {
        case .usage:
            return "Usage: apple-speech-transcriber AUDIO_WAV LOCALE or --check LOCALE"
        case .unavailable:
            return "Apple SpeechTranscriber is unavailable on this device"
        case .unsupportedLocale(let locale):
            return "Apple SpeechTranscriber does not support locale: \(locale)"
        case .uninstalledLocale(let locale):
            return "Apple SpeechTranscriber locale asset is not installed: \(locale)"
        case .missingTimeRange:
            return "Apple SpeechTranscriber returned final text without an audio time range"
        case .emptyTranscript:
            return "Apple SpeechTranscriber returned no final text"
        }
    }
}

func localeMatches(_ candidate: Locale, _ requested: Locale) -> Bool {
    candidate.identifier(.bcp47) == requested.identifier(.bcp47)
}

func encodeJSON<T: Encodable>(_ value: T) throws {
    let encoder = JSONEncoder()
    encoder.outputFormatting = [.prettyPrinted, .sortedKeys, .withoutEscapingSlashes]
    let data = try encoder.encode(value)
    FileHandle.standardOutput.write(data)
    FileHandle.standardOutput.write(Data("\n".utf8))
}

@main
struct AppleSpeechTranscriberCLI {
    static func main() async {
        do {
            try await run()
        } catch {
            FileHandle.standardError.write(Data("Error: \(error)\n".utf8))
            Foundation.exit(1)
        }
    }

    static func run() async throws {
        let arguments = CommandLine.arguments
        if arguments.count == 3 && arguments[1] == "--check" {
            let requested = Locale(identifier: arguments[2])
            let supportedLocales = await SpeechTranscriber.supportedLocales
            let installedLocales = await SpeechTranscriber.installedLocales
            try encodeJSON(
                SupportPayload(
                    available: SpeechTranscriber.isAvailable,
                    locale: requested.identifier(.bcp47),
                    supported: supportedLocales.contains {
                        localeMatches($0, requested)
                    },
                    installed: installedLocales.contains {
                        localeMatches($0, requested)
                    }
                )
            )
            return
        }
        guard arguments.count == 3 else {
            throw CLIError.usage
        }

        let audioURL = URL(fileURLWithPath: arguments[1])
        let requested = Locale(identifier: arguments[2])
        guard SpeechTranscriber.isAvailable else {
            throw CLIError.unavailable
        }
        let supportedLocales = await SpeechTranscriber.supportedLocales
        guard supportedLocales.contains(where: { localeMatches($0, requested) }) else {
            throw CLIError.unsupportedLocale(requested.identifier(.bcp47))
        }
        let installedLocales = await SpeechTranscriber.installedLocales
        guard installedLocales.contains(where: { localeMatches($0, requested) }) else {
            throw CLIError.uninstalledLocale(requested.identifier(.bcp47))
        }

        let file = try AVAudioFile(forReading: audioURL)
        let transcriber = SpeechTranscriber(
            locale: requested,
            transcriptionOptions: [],
            reportingOptions: [],
            attributeOptions: [.audioTimeRange]
        )
        let resultTask = Task<[Segment], Error> {
            var segments: [Segment] = []
            for try await result in transcriber.results {
                guard result.isFinal else { continue }
                let text = String(result.text.characters)
                    .trimmingCharacters(in: .whitespacesAndNewlines)
                guard !text.isEmpty else { continue }
                let timeRanges = result.text.runs.compactMap { run in
                    run.audioTimeRange
                }
                guard
                    let firstStart = timeRanges.map(\.start).min(),
                    let lastEnd = timeRanges.map(\.end).max()
                else {
                    throw CLIError.missingTimeRange
                }
                let start = CMTimeGetSeconds(firstStart)
                let end = CMTimeGetSeconds(lastEnd)
                segments.append(Segment(start: start, end: end, text: text))
            }
            return segments
        }

        let analyzer = SpeechAnalyzer(modules: [transcriber])
        if let lastSample = try await analyzer.analyzeSequence(from: file) {
            try await analyzer.finalizeAndFinish(through: lastSample)
        } else {
            await analyzer.cancelAndFinishNow()
        }
        let segments = try await resultTask.value
        guard !segments.isEmpty else {
            throw CLIError.emptyTranscript
        }
        try encodeJSON(
            TranscriptionPayload(
                engine: "Apple SpeechTranscriber",
                locale: requested.identifier(.bcp47),
                segments: segments,
                text: segments.map(\.text).joined(separator: "\n")
            )
        )
    }
}

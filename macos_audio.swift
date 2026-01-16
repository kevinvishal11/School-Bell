import Foundation
import CoreAudio

func getAllDevices() -> [AudioDeviceID] {
    var propertyAddress = AudioObjectPropertyAddress(
        mSelector: kAudioHardwarePropertyDevices,
        mScope: kAudioObjectPropertyScopeGlobal,
        mElement: kAudioObjectPropertyElementMain
    )
    var dataSize: UInt32 = 0
    AudioObjectGetPropertyDataSize(AudioObjectID(kAudioObjectSystemObject), &propertyAddress, 0, nil, &dataSize)
    let deviceCount = Int(dataSize) / MemoryLayout<AudioDeviceID>.size
    var deviceIDs = [AudioDeviceID](repeating: 0, count: deviceCount)
    AudioObjectGetPropertyData(AudioObjectID(kAudioObjectSystemObject), &propertyAddress, 0, nil, &dataSize, &deviceIDs)
    return deviceIDs
}

func getDeviceName(deviceID: AudioDeviceID) -> String {
    var propertyAddress = AudioObjectPropertyAddress(
        mSelector: kAudioDevicePropertyDeviceNameCFString,
        mScope: kAudioObjectPropertyScopeGlobal,
        mElement: kAudioObjectPropertyElementMain
    )
    var name: CFString = "" as CFString
    var dataSize = UInt32(MemoryLayout<CFString>.size)
    // We use a pointer to the CFString variable to avoid the warning about forming UnsafeMutableRawPointer to CFString
    let status = withUnsafeMutablePointer(to: &name) { ptr in
        AudioObjectGetPropertyData(deviceID, &propertyAddress, 0, nil, &dataSize, ptr)
    }
    return (status == noErr) ? (name as String) : "Unknown"
}

func isOutputDevice(deviceID: AudioDeviceID) -> Bool {
    var propertyAddress = AudioObjectPropertyAddress(
        mSelector: kAudioDevicePropertyStreams,
        mScope: kAudioObjectPropertyScopeOutput,
        mElement: kAudioObjectPropertyElementMain
    )
    var dataSize: UInt32 = 0
    AudioObjectGetPropertyDataSize(deviceID, &propertyAddress, 0, nil, &dataSize)
    return dataSize > 0
}

func setDefaultOutputDevice(deviceID: AudioDeviceID) {
    var propertyAddress = AudioObjectPropertyAddress(
        mSelector: kAudioHardwarePropertyDefaultOutputDevice,
        mScope: kAudioObjectPropertyScopeGlobal,
        mElement: kAudioObjectPropertyElementMain
    )
    var deviceID = deviceID
    let dataSize = UInt32(MemoryLayout<AudioDeviceID>.size)
    AudioObjectSetPropertyData(AudioObjectID(kAudioObjectSystemObject), &propertyAddress, 0, nil, dataSize, &deviceID)
}

let args = CommandLine.arguments
if args.count < 2 {
    // List devices
    for d in getAllDevices() where isOutputDevice(deviceID: d) {
        print(getDeviceName(deviceID: d))
    }
} else {
    // Set device
    let target = args[1...].joined(separator: " ")
    let devices = getAllDevices()
    if let match = devices.first(where: { isOutputDevice(deviceID: $0) && getDeviceName(deviceID: $0) == target }) {
        setDefaultOutputDevice(deviceID: match)
        print("Success")
    } else {
        print("Not Found")
        exit(1)
    }
}

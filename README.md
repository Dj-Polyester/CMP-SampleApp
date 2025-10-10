This is a sample slides Compose Multiplatform project.

# Table of Contents

- [History](#history)
  - [React and Flutter](#react-and-flutter)
  - [Jetpack Compose](#jetpack-compose)
  - [Kotlin and Compose Multiplatform](#kotlin-and-compose-multiplatform)
- [Setting up Compose Multiplatform for a Specific Platform](#setting-up-compose-multiplatform-for-a-specific-platform)
  - [Android](#android)
    - [Setting up](#setting-up)
    - [Debugging the Application](#debugging-the-application)
  - [iOS](#ios)
  - [Web](#web)
  - [Desktop](#desktop)

# History

## React and Flutter

The traditional methods in mobile app development required platform specific knowledge and expertise. They mostly separated the *user interfaces* (UI, i.e. XML files in Android) and logic (i.e. Java or Kotlin files in Android) providing bridging solutions between them. They required extensive bookkeeping to manually write logic to update the underlying data. *React* (2015) of Meta introduced a different approach, with *Flutter* (2018) of Google following along as a direct competitor. The new *state management* philosophy combines the logic and UI of the app in a single codebase reflecting changes in the data automatically. This greatly reduced the complexity of debugging and testing.

For comparison, Flutter differs in its performance using an optimized *software development kit* (SDK) and programming language *Dart*. React doesn't have its own SDK as it uses existing compilers and tools. React uses *JavaScript* as programming language which was originally designed to add interactivity and dynamic behavior to web pages. Its wide adoption across platforms and technologies makes JavaScript a preferred programming language, but this versatility comes at the cost of runtime performance. Its dynamic typing and lack of exception handling for its `undefined` value unlike statically typed Dart with null checks built-in by default makes it a less safe option. In React, drawing occurs with bridge calls that invoke native components. This introduces another overhead, whereas Flutter alleviates this with its own graphics engine Skia. One thing I liked about Flutter is the components (i.e. *widgets*) are self-contained - the developer could see everything about a component in itself. For example, they take UI parameters in their constructors as opposed to separate CSS stylesheets in React. For these reasons, I sticked to Flutter for some time until I came across Compose Multiplatform.

## Jetpack Compose

Jetbrains, the company behind Android Studio, *integrated development environments* (IDE) such as IntelliJ IDEA and the programming language *Kotlin* has introduced new technologies in last few years. *Jetpack Compose* (JC), one such technology in the Kotlin ecosystem. Kotlin is syntactically designed to be a concise and safe. The syntax has less boilerplate code and the language is statically typed with null safety features like Dart. Kotlin projects tend to be more readable with smoother debugging and testing experience. The downside of earlier UI frameworks was their verbosity. For example, many Flutter widgets require an optional child or children property, and custom widgets must implement a build method that runs on each rebuild. In contrast, Jetpack Compose components, *composables*, leverage Kotlin’s syntax by allowing trailing lambdas that return child composables. Furthermore, custom composables are simply function definitions that describe the UI instructions for rebuilding. JC is now integrated into the Android SDK as the official toolkit for building native UIs.

## Kotlin and Compose Multiplatform

*Kotlin Multiplatform* (KMP) is another technology used by the Kotlin ecosystem that allows sharing the same Kotlin code across different platforms (i.e. Android, iOS, Web, Desktop (JVM)). The upcoming sections are from the contents of the README file that comes with a starter project which is available [here](https://www.jetbrains.com/help/kotlin-multiplatform-dev/compose-multiplatform-create-first-app.html#create-a-project).

* [/composeApp](./composeApp/src) is for code that will be shared across your Compose Multiplatform applications.
  It contains several subfolders:
  - [commonMain](./composeApp/src/commonMain/kotlin) is for code that’s common for all targets.
  - Other folders are for Kotlin code that will be compiled for only the platform indicated in the folder name.
    For example, if you want to use Apple’s CoreCrypto for the iOS part of your Kotlin app,
    the [iosMain](./composeApp/src/iosMain/kotlin) folder would be the right place for such calls.
    Similarly, if you want to edit the Desktop (JVM) specific part, the [jvmMain](./composeApp/src/jvmMain/kotlin)
    folder is the appropriate location.

* [/iosApp](./iosApp/iosApp) contains iOS applications. Even if you’re sharing your UI with Compose Multiplatform,
  you need this entry point for your iOS app. This is also where you should add SwiftUI code for your project.

JC is also integrated into KMP, forming a stack known as *Compose Multiplatform* (CMP).

# Setting up Compose Multiplatform for a Specific Platform

Setting up CMP is not as uniform as the development process itself. The following sections describe the setup procedure for each platform, on an Arch Linux system.

Kotlin and Java projects use a build automation tool called *Gradle*. Gradle organizes files as projects in hierarchical manner expressed as `:subproject:subsubproject:...`. Each project has its own configuration in a `build.gradle` file located in its root directory.
These projects can be included in a `settings.gradle` file and `gradle projects` give list of all these projects within a directory. The
developer doesn't need to install Gradle manually as a binary (`gradlew`) is provided with each KMP and Android project. `android_debug` script handles all of these by itself. It also includes some preprocessing steps for a
pipeline with less warnings and errors.

## Android

The most wellknown and maybe the easiest way of working with Android SDK is Android Studio (I didn't check Jetbrains IDEs). However, the program is resource intensive as it was very sluggish on my system with limited resources. I managed to get a CMP program running without Android Studio and explain how I did it in this part.

The Android SDK is a collection of command-line tools, build tools, platform tools, and platforms, each associated with an API level. For example, API level 36 corresponds to the latest Android version at the time of writing, which was Android 16. `sdkmanager` is a command line utility in command-line tools that is used for installing other components. *Android Debug Bridge* (`adb`) is another such utility that lets user run terminal commands on a device.

### Setting up

The following command installs command-line tools
```bash
yay -S android-sdk-cmdline-tools-latest
```
Normally, the SDK location is `/opt/android_sdk`. In order to use `sdkmanager` and `adb` system-wide, one needs to set the appropriate environment variables.
```bash
export ANDROID_HOME=[sdk_location]
export PATH=$PATH:$ANDROID_HOME/platform-tools:$ANDROID_HOME/cmdline-tools/latest/bin
```
The platform tools is available through the following command
```bash
yay -S android-sdk-platform-tools
```
or `sdkmanager` can be used as well. A typical SDK installation then is as follows
```bash
sdkmanager "platforms;android-[version]" "build-tools;[version]"
sdkmanager --licenses
sdkmanager --update
```

### Debugging the Application

In this project, there is one subproject `composeApp`. To build a debug APK, one needs to run an `assembleDebug` task.
```bash
./gradlew :[subproject]:assembleDebug
```
The generated debug file is in `[subproject]/build/outputs/apk/debug/[subproject]-debug.apk` directory. The next step is to install the APK.
```bash
adb -[wiredFlag] install [file_path]
```
A device can be either physical (e.g. a smartphone) or virtual (i.e. an emulator). Virtual devices and wirelessly connected physical devices use `wiredFlag=e` whereas devices connected via a cable use `wiredFlag=e`. The install command is enough if there is only one physical device with specific type of medium (wireless or wired) or one emulator running. Otherwise, one needs to give device's serial number via `-s` flag. The command `adb devices` lists the connected devices with aforementioned properties.

The application now can be run. We will tell Activity Manager to start the specified activity and perform the action defined by an intent. The activities and their intents are defined in `AndroidManifest.xml` file.
```xml
<activity
    android:exported="true"
    android:name=".MainActivity">
    <intent-filter>
        <action android:name="android.intent.action.MAIN" />
        <category android:name="android.intent.category.LAUNCHER" />
    </intent-filter>
</activity>
```
The intent with action `MAIN` has category `LAUNCHER` which denotes the entry point of the application. This can be confirmed via following command that lists intent filters for each activity
```bash
adb shell dumpsys package [package_name]
```
The following command runs the application
```bash
adb shell am start -a android.intent.action.MAIN -n [package_name]/.MainActivity
```
It is possible to log via adb
```bash
adb logcat [log_tag]:D *:S
```
Where `[log_tag]:D` shows all logs with tag `log_tag` with debug level, and `*:S` silences all other outputs.

## iOS

Work in progress.

## Web

Work in progress.

## Desktop

Work in progress.

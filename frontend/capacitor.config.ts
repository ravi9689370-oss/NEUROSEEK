import { CapacitorConfig } from '@capacitor/cli'

const config: CapacitorConfig = {
  appId: 'ai.neuroseek.app',
  appName: 'NeuroSeek AI',
  webDir: 'out',
  server: {
    androidScheme: 'https',
    cleartext: true,
  },
  android: {
    buildOptions: {
      keystorePath: undefined,
      keystoreAlias: undefined,
      keystorePassword: undefined,
      keyPassword: undefined,
    },
    allowMixedContent: true,
    captureInput: true,
    webContentsDebuggingEnabled: true,
  },
  ios: {
    contentInset: 'automatic',
    scrollEnabled: true,
    limitsNavigationsToAppBoundDomains: true,
  },
  plugins: {
    SplashScreen: {
      launchShowDuration: 2000,
      backgroundColor: '#0ea5e9',
      showSpinner: false,
      androidScaleType: 'CENTER_CROP',
      splashFullScreen: true,
      splashImmersive: true,
    },
    StatusBar: {
      style: 'DARK',
      backgroundColor: '#0ea5e9',
    },
    Keyboard: {
      resize: 'body',
      style: 'DARK',
      resizeOnFullScreen: true,
    },
    LocalNotifications: {
      smallIcon: 'ic_stat_icon_config_sample',
      iconColor: '#0ea5e9',
    },
    PushNotifications: {
      presentationOptions: ['badge', 'sound', 'alert'],
    },
    CapacitorHttp: {
      enabled: true,
    },
  },
}

export default config
// Firebase Auth is the SAME identity layer AI Labs' own frontend uses to get a
// verifiable Microsoft ID token (see ai-labs-frontend/src/config/firebase.js).
// AI Labs' /auth/oauth-login verifies this Firebase ID token server-side, so
// this project reuses the same pattern rather than talking to Azure directly.
import { initializeApp } from 'firebase/app'
import { getAuth, OAuthProvider, signInWithPopup } from 'firebase/auth'

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
}

// Only usable once real values are supplied via frontend/.env (VITE_FIREBASE_*
// and VITE_MICROSOFT_CLIENT_ID) — same prerequisite ai-labs-frontend has.
export const microsoftSsoConfigured =
  !!firebaseConfig.apiKey && !!import.meta.env.VITE_MICROSOFT_CLIENT_ID

let app: ReturnType<typeof initializeApp> | null = null

function getFirebaseApp() {
  if (!app) app = initializeApp(firebaseConfig)
  return app
}

/** Opens the Microsoft popup via Firebase and returns a Firebase ID token
 *  suitable for AI Labs' `/auth/oauth-login` (and thus our `/auth/microsoft`). */
export async function signInWithMicrosoft(): Promise<string> {
  const auth = getAuth(getFirebaseApp())
  const provider = new OAuthProvider('microsoft.com')
  provider.setCustomParameters({ prompt: 'select_account' })
  provider.addScope('user.read')
  provider.addScope('email')
  provider.addScope('openid')
  provider.addScope('profile')

  const result = await signInWithPopup(auth, provider)
  return result.user.getIdToken()
}

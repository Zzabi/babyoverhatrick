/**
 * Auth helpers for sending requests to the FastAPI backend.
 * The backend validates Clerk JWTs via the JWKS endpoint.
 *
 * Usage in a component:
 *   const { getToken } = useAuth();
 *   const token = await getToken();
 *   await api.startSession(body, token ?? undefined);
 */

import { useAuth } from "@clerk/clerk-react";

/**
 * Returns an Authorization header object if the user is signed in,
 * or an empty object for guest requests.
 */
export async function buildAuthHeaders(
  getToken: ReturnType<typeof useAuth>["getToken"]
): Promise<Record<string, string>> {
  try {
    const token = await getToken();
    if (token) return { Authorization: `Bearer ${token}` };
  } catch {
    // not signed in — guest mode
  }
  return {};
}

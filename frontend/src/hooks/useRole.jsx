/**
 * The acting demonstration role.
 *
 * One selector at the top of the application decides which identity every API
 * call is made as. Role is held here rather than per screen so that switching it
 * changes the whole interface at once — the queue, the register and the case
 * list all narrow together, which is the point being demonstrated.
 *
 * This is not authentication. There is no password, session or token anywhere in
 * the prototype; the role is chosen from a list. What makes it more than a set
 * of buttons is that the API enforces the scope and the permissions on its side,
 * so a role that cannot close a case is refused by the server, not merely denied
 * a button.
 */

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import api, { setActiveUser } from '../services/api'

const STORAGE_KEY = 'nirikshan.role'
const FALLBACK = 'ministry.officer'

const RoleContext = createContext(null)

function readStored() {
  try {
    return window.localStorage.getItem(STORAGE_KEY) || FALLBACK
  } catch {
    // Private browsing, or server-side rendering during the page tests.
    return FALLBACK
  }
}

export function RoleProvider({ children }) {
  const [username, setUsername] = useState(readStored)
  const [directory, setDirectory] = useState({ users: [], roles: [], notice: '' })

  // Set before the first render commits so the initial data fetches on every
  // screen already carry the identity header.
  setActiveUser(username)

  useEffect(() => {
    setActiveUser(username)
    try {
      window.localStorage.setItem(STORAGE_KEY, username)
    } catch {
      /* not being able to remember the choice is not worth an error */
    }
  }, [username])

  useEffect(() => {
    let cancelled = false
    api
      .roles()
      .then((data) => !cancelled && setDirectory(data))
      .catch(() => {
        /* the header falls back to a plain label if the directory is unreachable */
      })
    return () => {
      cancelled = true
    }
  }, [])

  const user = useMemo(
    () => directory.users?.find((u) => u.username === username) || null,
    [directory, username],
  )

  const can = useCallback(
    (capability) => Boolean(user?.capabilities?.includes(capability)),
    [user],
  )

  const value = useMemo(
    () => ({
      username,
      setUsername,
      user,
      users: directory.users || [],
      roles: directory.roles || [],
      notice: directory.notice || '',
      can,
      // Screens re-fetch on this key so a role change reloads their data.
      roleKey: username,
    }),
    [username, user, directory, can],
  )

  return <RoleContext.Provider value={value}>{children}</RoleContext.Provider>
}

export function useRole() {
  const ctx = useContext(RoleContext)
  if (!ctx) {
    // Rendering a screen outside the provider should not crash the page test.
    return {
      username: FALLBACK,
      setUsername: () => {},
      user: null,
      users: [],
      roles: [],
      notice: '',
      can: () => false,
      roleKey: FALLBACK,
    }
  }
  return ctx
}

export default useRole

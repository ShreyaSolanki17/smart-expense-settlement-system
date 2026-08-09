import { useEffect, useState } from 'react'
import { api } from './api'
import { graphqlApi } from './graphql'

function useAuth() {
  const [token, setToken] = useState(() => localStorage.getItem('token'))
  const [user, setUser] = useState(null)

  useEffect(() => {
    if (!token) {
      setUser(null)
      return
    }
    api.me(token).then(setUser).catch(() => {
      localStorage.removeItem('token')
      setToken(null)
    })
  }, [token])

  function login(t) {
    localStorage.setItem('token', t)
    setToken(t)
  }

  function logout() {
    localStorage.removeItem('token')
    setToken(null)
  }

  return { token, user, login, logout }
}

function AuthScreen({ onLogin }) {
  const [mode, setMode] = useState('login')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')

  async function submit(e) {
    e.preventDefault()
    setError('')
    try {
      const data =
        mode === 'login' ? await api.login(username, password) : await api.register(username, password)
      onLogin(data.token)
    } catch (err) {
      setError(err.message)
    }
  }

  async function tryDemo() {
    setError('')
    try {
      const data = await api.demoLogin()
      onLogin(data.token)
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="auth-screen">
      <h1>Smart Expense Settlement</h1>
      <button className="demo-button" onClick={tryDemo}>
        Try demo
      </button>
      <p className="muted">or</p>
      <form onSubmit={submit}>
        <input placeholder="username" value={username} onChange={(e) => setUsername(e.target.value)} />
        <input
          placeholder="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <button type="submit">{mode === 'login' ? 'Log in' : 'Sign up'}</button>
      </form>
      {error && <p className="error">{error}</p>}
      <button className="link" onClick={() => setMode(mode === 'login' ? 'register' : 'login')}>
        {mode === 'login' ? 'Need an account? Sign up' : 'Have an account? Log in'}
      </button>
    </div>
  )
}

function CreateGroup({ token, currentUser, onCreated }) {
  const [name, setName] = useState('')
  const [query, setQuery] = useState('')
  const [matches, setMatches] = useState([])
  const [members, setMembers] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    if (query.trim().length < 2) {
      setMatches([])
      return
    }
    const timer = setTimeout(() => {
      api.searchUsers(token, query).then(setMatches).catch(() => setMatches([]))
    }, 250)
    return () => clearTimeout(timer)
  }, [query, token])

  function addMember(u) {
    if (!members.some((m) => m.id === u.id)) setMembers([...members, u])
    setQuery('')
    setMatches([])
  }

  async function submit(e) {
    e.preventDefault()
    setError('')
    try {
      const group = await api.createGroup(token, name, members.map((m) => m.id))
      setName('')
      setMembers([])
      onCreated(group)
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <form className="create-group" onSubmit={submit}>
      <input placeholder="new group name" value={name} onChange={(e) => setName(e.target.value)} />
      <div className="member-picker">
        <input
          placeholder="add member by username"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        {matches.length > 0 && (
          <ul className="suggestions">
            {matches.map((u) => (
              <li key={u.id} onClick={() => addMember(u)}>
                {u.username}
              </li>
            ))}
          </ul>
        )}
      </div>
      {members.length > 0 && (
        <div className="chips">
          {[currentUser?.username, ...members.map((m) => m.username)].filter(Boolean).map((n) => (
            <span className="chip" key={n}>
              {n}
            </span>
          ))}
        </div>
      )}
      <button type="submit" disabled={!name.trim()}>
        Create group
      </button>
      {error && <p className="error">{error}</p>}
    </form>
  )
}

function AddExpense({ token, group, onAdded }) {
  const [description, setDescription] = useState('')
  const [amount, setAmount] = useState('')
  const [paidBy, setPaidBy] = useState(group.members[0]?.id ?? '')
  const [error, setError] = useState('')

  async function submit(e) {
    e.preventDefault()
    setError('')
    try {
      await graphqlApi.createExpense(token, {
        group: group.id,
        description,
        amount,
        paid_by: paidBy,
      })
      setDescription('')
      setAmount('')
      onAdded()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <form className="add-expense" onSubmit={submit}>
      <input
        placeholder="description"
        value={description}
        onChange={(e) => setDescription(e.target.value)}
      />
      <input
        placeholder="amount"
        type="number"
        step="0.01"
        min="0.01"
        value={amount}
        onChange={(e) => setAmount(e.target.value)}
      />
      <select value={paidBy} onChange={(e) => setPaidBy(Number(e.target.value))}>
        {group.members.map((m) => (
          <option key={m.id} value={m.id}>
            paid by {m.username}
          </option>
        ))}
      </select>
      <button type="submit" disabled={!description.trim() || !amount}>
        Add expense (splits equally)
      </button>
      {error && <p className="error">{error}</p>}
    </form>
  )
}

function Balances({ token, group, transactions, onSettled }) {
  const [error, setError] = useState('')
  const [settling, setSettling] = useState(null)

  function memberName(id) {
    return group.members.find((m) => m.id === id)?.username ?? id
  }

  async function settle(t) {
    setSettling(`${t.fromUser}-${t.toUser}`)
    setError('')
    try {
      await graphqlApi.createSettlement(token, {
        group: group.id,
        from_user: t.fromUser,
        to_user: t.toUser,
        amount: t.amount,
      })
      onSettled()
    } catch (err) {
      setError(err.message)
    } finally {
      setSettling(null)
    }
  }

  return (
    <div className="balances">
      <h3>Suggested settlements</h3>
      {transactions.length === 0 && <p className="muted">Everyone's settled up.</p>}
      <ul>
        {transactions.map((t) => (
          <li key={`${t.fromUser}-${t.toUser}`}>
            {memberName(t.fromUser)} owes {memberName(t.toUser)} ${t.amount}
            <button
              disabled={settling === `${t.fromUser}-${t.toUser}`}
              onClick={() => settle(t)}
            >
              Mark settled
            </button>
          </li>
        ))}
      </ul>
      {error && <p className="error">{error}</p>}
    </div>
  )
}

function GroupDetail({ token, group }) {
  const [expenses, setExpenses] = useState([])
  const [balances, setBalances] = useState([])
  const [error, setError] = useState('')

  // Was listExpenses() + getBalances() — one GraphQL query now covers both.
  function load() {
    graphqlApi
      .groupDetail(token, group.id)
      .then((data) => {
        setExpenses(data.expenses)
        setBalances(data.balances)
      })
      .catch((err) => setError(err.message))
  }

  useEffect(load, [token, group.id])

  return (
    <div className="group-detail">
      <h2>{group.name}</h2>
      <p className="muted">members: {group.members.map((m) => m.username).join(', ')}</p>

      <AddExpense token={token} group={group} onAdded={load} />

      <h3>Expenses</h3>
      <ul className="expenses">
        {expenses.map((e) => (
          <li key={e.id}>
            {e.description} — ${e.amount} (paid by {e.paidBy.username})
          </li>
        ))}
      </ul>

      <Balances token={token} group={group} transactions={balances} onSettled={load} />
      {error && <p className="error">{error}</p>}
    </div>
  )
}

function Notifications({ token }) {
  const [items, setItems] = useState([])
  const [open, setOpen] = useState(false)

  function load() {
    api
      .listNotifications(token)
      .then((data) => setItems(data.results ?? data))
      .catch(() => {})
  }

  useEffect(() => {
    load()
    const timer = setInterval(load, 15000)
    return () => clearInterval(timer)
  }, [token])

  async function markRead(notification) {
    if (notification.read) return
    await api.markNotificationRead(token, notification.id)
    load()
  }

  const unread = items.filter((n) => !n.read).length

  return (
    <div className="notifications">
      <button className="bell" onClick={() => setOpen((o) => !o)}>
        🔔{unread > 0 && <span className="badge">{unread}</span>}
      </button>
      {open && (
        <ul className="notification-list">
          {items.length === 0 && <li className="muted">No notifications.</li>}
          {items.map((n) => (
            <li key={n.id} className={n.read ? "read" : "unread"} onClick={() => markRead(n)}>
              {n.message}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function Dashboard({ token, user, onLogout }) {
  const [groups, setGroups] = useState([])
  const [selectedId, setSelectedId] = useState(null)

  function loadGroups() {
    api.listGroups(token).then((data) => setGroups(data.results ?? data))
  }

  useEffect(loadGroups, [token])

  const selected = groups.find((g) => g.id === selectedId) ?? null

  return (
    <div className="dashboard">
      <aside>
        <div className="user-bar">
          <span>{user?.username}</span>
          <Notifications token={token} />
          <button className="link" onClick={onLogout}>
            Log out
          </button>
        </div>
        <CreateGroup
          token={token}
          currentUser={user}
          onCreated={(g) => {
            loadGroups()
            setSelectedId(g.id)
          }}
        />
        <ul className="group-list">
          {groups.map((g) => (
            <li
              key={g.id}
              className={g.id === selectedId ? 'active' : ''}
              onClick={() => setSelectedId(g.id)}
            >
              {g.name}
            </li>
          ))}
        </ul>
      </aside>
      <main>
        {selected ? (
          <GroupDetail token={token} group={selected} />
        ) : (
          <p className="muted">Select or create a group to get started.</p>
        )}
      </main>
    </div>
  )
}

export default function App() {
  const { token, user, login, logout } = useAuth()

  if (!token || !user) {
    return <AuthScreen onLogin={login} />
  }

  return <Dashboard token={token} user={user} onLogout={logout} />
}

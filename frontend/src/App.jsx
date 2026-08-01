import { useEffect, useState } from 'react'
import { api } from './api'

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
      await api.createExpense(token, {
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

function Balances({ token, group, refreshKey }) {
  const [transactions, setTransactions] = useState([])
  const [error, setError] = useState('')
  const [settling, setSettling] = useState(null)

  function memberName(id) {
    return group.members.find((m) => m.id === id)?.username ?? id
  }

  function load() {
    api
      .getBalances(token, group.id)
      .then(setTransactions)
      .catch((err) => setError(err.message))
  }

  useEffect(load, [token, group.id, refreshKey])

  async function settle(t) {
    setSettling(`${t.from_user}-${t.to_user}`)
    setError('')
    try {
      await api.createSettlement(token, {
        group: group.id,
        from_user: t.from_user,
        to_user: t.to_user,
        amount: t.amount,
      })
      load()
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
          <li key={`${t.from_user}-${t.to_user}`}>
            {memberName(t.from_user)} owes {memberName(t.to_user)} ${t.amount}
            <button
              disabled={settling === `${t.from_user}-${t.to_user}`}
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
  const [refreshKey, setRefreshKey] = useState(0)

  function loadExpenses() {
    api.listExpenses(token, group.id).then((data) => setExpenses(data.results ?? data))
  }

  useEffect(loadExpenses, [token, group.id])

  function refresh() {
    loadExpenses()
    setRefreshKey((k) => k + 1)
  }

  return (
    <div className="group-detail">
      <h2>{group.name}</h2>
      <p className="muted">members: {group.members.map((m) => m.username).join(', ')}</p>

      <AddExpense token={token} group={group} onAdded={refresh} />

      <h3>Expenses</h3>
      <ul className="expenses">
        {expenses.map((e) => (
          <li key={e.id}>
            {e.description} — ${e.amount} (paid by {group.members.find((m) => m.id === e.paid_by)?.username})
          </li>
        ))}
      </ul>

      <Balances token={token} group={group} refreshKey={refreshKey} />
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

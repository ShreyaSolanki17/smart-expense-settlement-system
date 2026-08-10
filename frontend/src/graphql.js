const GRAPHQL_URL = import.meta.env.VITE_GRAPHQL_URL || 'http://localhost:8000/graphql/'

async function graphqlRequest(token, query, variables) {
  const res = await fetch(GRAPHQL_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Token ${token}` } : {}),
    },
    body: JSON.stringify({ query, variables }),
  })
  const { data, errors } = await res.json()
  if (errors?.length) throw new Error(errors[0].message)
  return data
}

// One round trip for what used to be listExpenses() + getBalances().
const GROUP_DETAIL_QUERY = `
  query GroupDetail($groupId: ID!) {
    expenses(groupId: $groupId) {
      id
      description
      amount
      paidBy { username }
    }
    balances(groupId: $groupId) {
      fromUser
      toUser
      amount
    }
  }
`

const CREATE_EXPENSE_MUTATION = `
  mutation CreateExpense($group: ID!, $description: String!, $amount: Decimal!, $paidBy: ID!, $splits: [ExpenseSplitInput!]) {
    createExpense(group: $group, description: $description, amount: $amount, paidBy: $paidBy, splits: $splits) {
      expense { id }
    }
  }
`

const CREATE_SETTLEMENT_MUTATION = `
  mutation CreateSettlement($group: ID!, $fromUser: ID!, $toUser: ID!, $amount: Decimal!) {
    createSettlement(group: $group, fromUser: $fromUser, toUser: $toUser, amount: $amount) {
      settlement { id }
    }
  }
`

export const graphqlApi = {
  groupDetail: (token, groupId) => graphqlRequest(token, GROUP_DETAIL_QUERY, { groupId }),

  createExpense: (token, { group, description, amount, paid_by, splits }) =>
    graphqlRequest(token, CREATE_EXPENSE_MUTATION, {
      group,
      description,
      amount,
      paidBy: paid_by,
      splits: splits ? splits.map((s) => ({ user: s.user, shareAmount: s.share_amount })) : null,
    }),

  createSettlement: (token, { group, from_user, to_user, amount }) =>
    graphqlRequest(token, CREATE_SETTLEMENT_MUTATION, {
      group,
      fromUser: from_user,
      toUser: to_user,
      amount,
    }),
}

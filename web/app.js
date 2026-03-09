const STORAGE_KEY = "finance-tracker-web-v1";

function readState() {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return { transactions: [], budgets: {} };
  return JSON.parse(raw);
}

function saveState(state) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

function currency(value) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(value);
}

function sanitizeCategory(category) {
  return category.trim().toLowerCase();
}

function computeSummary(transactions) {
  const income = transactions.filter(t => t.kind === "income").reduce((a, t) => a + t.amount, 0);
  const expense = transactions.filter(t => t.kind === "expense").reduce((a, t) => a + t.amount, 0);
  const savings = income - expense;
  const rate = income > 0 ? (savings / income) * 100 : 0;
  return { income, expense, savings, rate };
}

function computeExpenseByCategory(transactions) {
  const result = {};
  transactions.filter(t => t.kind === "expense").forEach(t => {
    result[t.category] = (result[t.category] || 0) + t.amount;
  });
  return result;
}

function render() {
  const state = readState();
  const summary = computeSummary(state.transactions);
  const expenseByCategory = computeExpenseByCategory(state.transactions);

  document.getElementById("totalIncome").textContent = currency(summary.income);
  document.getElementById("totalExpense").textContent = currency(summary.expense);
  document.getElementById("netSavings").textContent = currency(summary.savings);
  document.getElementById("savingsRate").textContent = `${summary.rate.toFixed(1)}%`;

  const table = document.getElementById("transactionTable");
  table.innerHTML = "";
  [...state.transactions]
    .sort((a, b) => (a.txDate < b.txDate ? 1 : -1))
    .forEach((t) => {
      const row = document.createElement("tr");
      row.innerHTML = `
        <td>${t.txDate}</td>
        <td>${t.kind}</td>
        <td>${t.category}</td>
        <td>${t.description || "-"}</td>
        <td class="amount-${t.kind}">${t.kind === "income" ? "+" : "-"}${currency(t.amount)}</td>
      `;
      table.appendChild(row);
    });

  const budgetList = document.getElementById("budgetList");
  budgetList.innerHTML = "";
  Object.entries(state.budgets).forEach(([category, budget]) => {
    const spent = expenseByCategory[category] || 0;
    const remaining = budget - spent;
    const item = document.createElement("div");
    item.className = "list-item";
    item.innerHTML = `
      <strong>${category}</strong>
      <div>Budget: ${currency(budget)} · Spent: ${currency(spent)}</div>
      <div class="${remaining < 0 ? "warn" : "ok"}">${remaining < 0 ? "Over by" : "Remaining"}: ${currency(Math.abs(remaining))}</div>
    `;
    budgetList.appendChild(item);
  });

  const bars = document.getElementById("expenseBars");
  bars.innerHTML = "";
  const max = Math.max(1, ...Object.values(expenseByCategory));
  Object.entries(expenseByCategory)
    .sort((a, b) => b[1] - a[1])
    .forEach(([category, amount]) => {
      const wrap = document.createElement("div");
      wrap.className = "bar-wrap";
      wrap.innerHTML = `
        <div class="bar-meta"><span>${category}</span><span>${currency(amount)}</span></div>
        <div class="bar"><div style="width:${(amount / max) * 100}%"></div></div>
      `;
      bars.appendChild(wrap);
    });
}

function setupForms() {
  const txForm = document.getElementById("transactionForm");
  txForm.txDate.value = new Date().toISOString().slice(0, 10);
  txForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const form = new FormData(txForm);
    const state = readState();
    state.transactions.push({
      kind: form.get("kind"),
      amount: Number(form.get("amount")),
      category: sanitizeCategory(form.get("category")),
      description: String(form.get("description") || "").trim(),
      txDate: form.get("txDate"),
    });
    saveState(state);
    txForm.reset();
    txForm.txDate.value = new Date().toISOString().slice(0, 10);
    render();
  });

  const budgetForm = document.getElementById("budgetForm");
  budgetForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const form = new FormData(budgetForm);
    const state = readState();
    const category = sanitizeCategory(form.get("category"));
    state.budgets[category] = Number(form.get("amount"));
    saveState(state);
    budgetForm.reset();
    render();
  });

  document.getElementById("resetData").addEventListener("click", () => {
    if (confirm("This will remove all local tracker data. Continue?")) {
      localStorage.removeItem(STORAGE_KEY);
      render();
    }
  });
}

setupForms();
render();

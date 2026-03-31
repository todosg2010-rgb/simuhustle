from flask import Flask, request, jsonify
import random
import os
from dataclasses import dataclass, asdict
from typing import List
import concurrent.futures

app = Flask(__name__)

# -----------------------------
# Data Models
# -----------------------------

@dataclass
class SimulationInputs:
    hustle: str
    weekly_hours: int
    starting_capital: float
    skill_level: int
    ad_budget_per_month: float
    price: float
    cost: float

@dataclass
class MonthlyResult:
    month: int
    traffic: int
    customers: int
    revenue: float
    expenses: float
    net_profit: float

# -----------------------------
# Hustle Profiles
# -----------------------------

HUSTLES = {
    "dropshipping": {"type": "ecommerce", "conversion": 0.017},
    "print_on_demand": {"type": "ecommerce", "conversion": 0.018},
    "amazon_fba": {"type": "ecommerce", "conversion": 0.025},
    "etsy_store": {"type": "ecommerce", "conversion": 0.022},
    "digital_products": {"type": "digital", "conversion": 0.03},
    "online_course": {"type": "course", "conversion": 0.012},
    "newsletter": {"type": "subscription", "conversion": 0.02},
    "affiliate_marketing": {"type": "affiliate", "conversion": 0.015},
    "micro_saas": {"type": "saas", "conversion": 0.01},
    "agency": {"type": "agency", "conversion": 0.004},
    "content_creator": {"type": "creator", "conversion": 0.008},
}

# -----------------------------
# Simulator Engine
# -----------------------------

class HustleSimulator:
    BASE_CPC = 0.50
    SKILL_MODIFIERS = {1: -0.005, 2: -0.002, 3: 0.0, 4: 0.003, 5: 0.006}

    def __init__(self, inputs: SimulationInputs):
        self.inputs = inputs
        self.profile = HUSTLES[inputs.hustle]
        self.capital = inputs.starting_capital
        self.ad_budget = inputs.ad_budget_per_month
        self.subscribers = 0
        self.clients = 0
        self.results: List[MonthlyResult] = []

    def rand(self, v):
        return random.uniform(1 - v, 1 + v)

    def traffic(self):
        cpc = self.BASE_CPC * self.rand(0.2)
        paid = int(self.ad_budget / cpc)
        organic = random.randint(100, 400)
        return paid + organic

    def conversion(self, month):
        base = self.profile["conversion"]
        skill = self.SKILL_MODIFIERS[self.inputs.skill_level]
        conv = base + skill
        conv *= (1 + month * 0.03)
        return max(0.001, conv * self.rand(0.2))

    def ecommerce(self, customers):
        revenue = customers * self.inputs.price
        cogs = customers * self.inputs.cost
        return revenue, cogs

    def digital(self, customers):
        revenue = customers * self.inputs.price
        cost = customers * (self.inputs.cost * 0.2)
        return revenue, cost

    def course(self, customers):
        revenue = customers * self.inputs.price
        cost = revenue * 0.1
        return revenue, cost

    def subscription(self, customers):
        self.subscribers += customers
        revenue = self.subscribers * self.inputs.price
        cost = revenue * 0.05
        return revenue, cost

    def affiliate(self, customers):
        commission = self.inputs.price * 0.3
        revenue = customers * commission
        cost = 0
        return revenue, cost

    def saas(self, customers):
        self.subscribers += customers
        revenue = self.subscribers * self.inputs.price
        server_cost = revenue * 0.1
        return revenue, server_cost

    def agency(self, customers):
        new_clients = max(0, customers // 3)
        self.clients += new_clients
        revenue = self.clients * self.inputs.price
        cost = revenue * 0.15
        return revenue, cost

    def creator(self, customers):
        revenue = customers * (self.inputs.price * 0.2)
        cost = revenue * 0.05
        return revenue, cost

    def simulate_month(self, month):
        traffic = self.traffic()
        conversion = self.conversion(month)
        customers = int(traffic * conversion)
        model = self.profile["type"]

        if model == "ecommerce":
            revenue, cost = self.ecommerce(customers)
        elif model == "digital":
            revenue, cost = self.digital(customers)
        elif model == "course":
            revenue, cost = self.course(customers)
        elif model == "subscription":
            revenue, cost = self.subscription(customers)
        elif model == "affiliate":
            revenue, cost = self.affiliate(customers)
        elif model == "saas":
            revenue, cost = self.saas(customers)
        elif model == "agency":
            revenue, cost = self.agency(customers)
        else:
            revenue, cost = self.creator(customers)

        expenses = cost + self.ad_budget
        profit = revenue - expenses
        self.capital += profit

        return traffic, customers, revenue, expenses, profit

    def run(self):
        total_profit = 0
        for month in range(1, 7):
            traffic, customers, revenue, expenses, profit = self.simulate_month(month)
            total_profit += profit
            self.results.append(MonthlyResult(month, traffic, customers, round(revenue, 2), round(expenses, 2), round(profit, 2)))

        return {
            "monthly_results": [asdict(m) for m in self.results],
            "total_profit": round(total_profit, 2),
            "final_capital": round(self.capital, 2)
        }

def run_simulation(inputs, scenario="base", runs=100):
    results = []
    for _ in range(runs):
        sim = HustleSimulator(inputs)
        results.append(sim.run())
    results.sort(key=lambda x: x["total_profit"])
    if scenario == "worst":
        return results[int(runs * 0.1)]
    if scenario == "best":
        return results[int(runs * 0.9)]
    return results[int(runs * 0.5)]

# -----------------------------
# Flask Routes
# -----------------------------

@app.route("/")
def home():
    with open("lanpage.html", "r", encoding="utf-8") as f:
        return f.read()

@app.route("/demo")
def demo():
    with open("demo.html", "r", encoding="utf-8") as f:
        return f.read()

@app.route("/personal-analysis")
def personal_analysis():
    with open("personal_analysis.html", "r", encoding="utf-8") as f:
        return f.read()

@app.route("/simulate", methods=["POST"])
def simulate():
    data = request.json
    inputs = SimulationInputs(
        hustle=data["hustle"],
        weekly_hours=data["weekly_hours"],
        starting_capital=data["starting_capital"],
        skill_level=data["skill_level"],
        ad_budget_per_month=data["ad_budget_per_month"],
        price=data["price"],
        cost=data["cost"]
    )
    result = run_simulation(inputs, data.get("scenario", "base"))
    return jsonify(result)

@app.route("/compare", methods=["POST"])
def compare():
    data = request.json
    inputs_a = SimulationInputs(
        hustle=data["a"]["hustle"],
        weekly_hours=data["a"]["weekly_hours"],
        starting_capital=data["a"]["starting_capital"],
        skill_level=data["a"]["skill_level"],
        ad_budget_per_month=data["a"]["ad_budget_per_month"],
        price=data["a"]["price"],
        cost=data["a"]["cost"]
    )
    inputs_b = SimulationInputs(
        hustle=data["b"]["hustle"],
        weekly_hours=data["b"]["weekly_hours"],
        starting_capital=data["b"]["starting_capital"],
        skill_level=data["b"]["skill_level"],
        ad_budget_per_month=data["b"]["ad_budget_per_month"],
        price=data["b"]["price"],
        cost=data["b"]["cost"]
    )
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_a = executor.submit(run_simulation, inputs_a, data["a"].get("scenario", "base"))
        future_b = executor.submit(run_simulation, inputs_b, data["b"].get("scenario", "base"))
        result_a = future_a.result()
        result_b = future_b.result()
    return jsonify({
        "a": result_a,
        "b": result_b,
        "winner": "a" if result_a["total_profit"] > result_b["total_profit"] else "b",
        "profit_difference": abs(result_a["total_profit"] - result_b["total_profit"]),
        "multiplier": max(result_a["total_profit"], result_b["total_profit"]) / max(min(abs(result_a["total_profit"]), abs(result_b["total_profit"])), 1)
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=False)

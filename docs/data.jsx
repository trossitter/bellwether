// data.jsx — Bellwether for Thesis. Population finding + five flagged subscribers.
// Exported to window for the other babel scripts.

const FLEET = {
  scored: 26584,           // active Thesis subscribers scored this cycle
  atRisk: 2247,            // flagged at risk this month
  reviewQueue: 41,         // escalated to a human rep for review this cycle
  showingTop: 5,
  pricePoint: 79,          // $/mo subscription
  cycleLabel: "Cycle 26 · June 2026",
  modelNote: "Scored nightly · gradient-boosted survival model + LLM message drafting",
};

// The population finding — one row per behavioral archetype Bellwether separates.
// rate = share of that archetype currently flagged at risk.
const ARCHETYPES = [
  { key: "price",     name: "Price",                 members: 17300, atRisk: 860, rate: 5,
    blurb: "Comparing cost after a plan or renewal email." },
  { key: "life",      name: "Life Change",           members: 6728,  atRisk: 638, rate: 9,
    blurb: "A move, a new baby, a busy stretch — life, not the product." },
  { key: "efficacy",  name: "Expectation Gap", members: 870,   atRisk: 190, rate: 22,
    blurb: "In the 4–6 month window, unsure it's working yet." },
  { key: "overstock", name: "Product Overstock",     members: 1009,  atRisk: 56,  rate: 6,
    blurb: "Taking it less often than it ships — bottles stacking up." },
  { key: "payment",   name: "Payment Declined",      members: 666,   atRisk: 503, rate: 76,
    blurb: "An expired or failed card, not a decision to leave." },
];

// risk tiers (treat score as churn-risk %). base rate ≈ 8.5%, so an elevated
// band starts well below 50. high (clay) ≥60, elevated (amber) 30–59, watch (sage) <30.
function tierOf(score) {
  if (score >= 60) return "high";
  if (score >= 30) return "elevated";
  return "watch";
}

const SUBSCRIBERS = [
  {
    id: "marguerite",
    archetype: "Payment Declined",
    archetypeKey: "payment",
    name: "Marguerite Vance",
    initials: "MV",
    location: "Marin County, CA",
    formula: "Clarity (Caffeine-Free)",
    formulaShort: "Clarity · CF",
    cadence: "Monthly · 28-day",
    tenureMonths: 14,
    tenureLabel: "14 months",
    ltv: 1106,
    nextRenewal: "Jun 12",
    score: 82,
    prevScore: 39,
    headline:
      "A 14-month subscriber one failed charge from silent churn — the card lapsed, not her intent.",
    factors: [
      { label: "Card declined ×2 (expired)", weight: 38, note: "Visa ·04 expired Jun 1" },
      { label: "Dunning emails unopened", weight: 16, note: "2 retries, no response" },
      { label: "14-month loyalty cohort", weight: 7, note: "Baseline cohort risk" },
      { label: "Usage stayed healthy", weight: -14, note: "Logged 22 of 30 days" },
    ],
    action: {
      kind: "Payment recovery",
      title: "One-tap card update — no offer, no friction",
      detail:
        "Send the pre-filled update link by SMS and email; hold the shipment five days instead of cancelling. No discount — she never chose to leave.",
      why:
        "This is involuntary churn. A win-back coupon would teach good customers to let cards lapse. The fix is removing 30 seconds of friction, not lowering the price.",
      effort: "Low touch · automated",
      cost: "$0 incentive",
    },
    alternatives: ["Pause one cycle, retry next month", "CX call if no update in 5 days"],
    measure: {
      liftPts: 54, ci: 8, holdoutPct: 10, checkBack: "Jun 19",
      success: "Card updated, shipment resumes on schedule",
      baseline: "Untreated declines recover at 18%",
    },
    message:
      "Your Clarity shipment is ready to go — we just need a quick payment update to keep it on its way. Takes about 30 seconds. No changes to your formula or cadence unless you want them.",
    judge: 4.6,
  },
  {
    id: "theo",
    archetype: "Life Change",
    archetypeKey: "life",
    name: "Theo Lindqvist",
    initials: "TL",
    location: "Seattle, WA",
    formula: "Clarity + Motivation",
    formulaShort: "Clarity + Motivation",
    cadence: "Monthly · 28-day",
    tenureMonths: 24,
    tenureLabel: "2 years",
    ltv: 1896,
    nextRenewal: "Jun 22",
    score: 34,
    prevScore: 18,
    headline:
      "Two years in, usage fell off a cliff and a support note mentions a newborn — life got loud, not disappointing.",
    factors: [
      { label: "Daily logging ↓ 70% (4 wk)", weight: 20, note: "From ~20 days to 6" },
      { label: "Support note: “slammed lately”", weight: 14, note: "Mentioned a new baby" },
      { label: "Opened pause-policy FAQ", weight: 9, note: "Looking for an exit ramp" },
      { label: "24 months, zero prior skips", weight: -17, note: "Deep loyalty signal" },
    ],
    action: {
      kind: "Pause offer",
      title: "Offer up to 3 months paused — formulas stay on file",
      detail:
        "Acknowledge the season of life directly and make pausing one tap. Keep his exact stack saved so resuming is effortless when things settle.",
      why:
        "He doesn't need a discount; he needs room. Forcing the renewal turns a loyal subscriber into a hard cancel. A pause keeps the relationship and pre-commits the return.",
      effort: "Low touch · one-tap",
      cost: "Deferred revenue, not lost",
    },
    alternatives: ["Switch to 60-day cadence", "CX check-in note, no offer"],
    measure: {
      liftPts: 23, ci: 7, holdoutPct: 10, checkBack: "Sep 22",
      success: "Schedules a pause and a resume date",
      baseline: "Untreated life-change churns at 41%",
    },
    message:
      "You've been with Thesis for over two years — that's not nothing. If life's gotten busier, you can pause for up to 3 months and pick back up whenever you're ready. Your formulas stay on file.",
    judge: 4.4,
  },
  {
    id: "priya",
    archetype: "Expectation Gap",
    archetypeKey: "efficacy",
    name: "Priya Anand",
    initials: "PA",
    location: "Brooklyn, NY",
    formula: "Confidence + Logic",
    formulaShort: "Confidence + Logic",
    cadence: "Monthly · 28-day",
    tenureMonths: 6,
    tenureLabel: "6 months",
    ltv: 474,
    nextRenewal: "Jun 16",
    score: 28,
    prevScore: 26,
    headline:
      "A newer subscriber at the expectation gap — results take longer than she thinks, and she's in the 4–6 month window where belief wavers.",
    factors: [
      { label: "Assessment never completed", weight: 18, note: "Skipped at onboarding" },
      { label: "Read “how long until” FAQ ×3", weight: 13, note: "Seeking reassurance" },
      { label: "6-month cohort cliff", weight: 10, note: "Highest-churn month" },
      { label: "Still opens every email", weight: -8, note: "Engaged, wants to believe" },
    ],
    action: {
      kind: "Education + assessment",
      title: "Surface the assessment and the 4–6 month efficacy note",
      detail:
        "Reframe “nothing dramatic yet” as “right on schedule.” Invite the 5-minute assessment, which usually surfaces a timing or stacking tweak worth staying for.",
      why:
        "Her churn is an information gap, not dissatisfaction. Education is cheaper and far more durable than a discount, and it builds the belief that carries her past month six.",
      effort: "Low touch · automated",
      cost: "$0",
    },
    alternatives: ["Pair with a coaching call", "Offer formula re-match"],
    measure: {
      liftPts: 19, ci: 6, holdoutPct: 10, checkBack: "Jul 16",
      success: "Completes assessment, renews Jun 16",
      baseline: "Untreated efficacy-gap churns at 34%",
    },
    message:
      "Most people who stick with Confidence + Logic notice the shift around months 4–6 — you're right in that window. If you haven't done the full assessment yet, it usually surfaces something useful about timing.",
    judge: 4.1,
  },
  {
    id: "marcus",
    archetype: "Price",
    archetypeKey: "price",
    name: "Marcus Bell",
    initials: "MB",
    location: "Columbus, OH",
    formula: "Energy + Clarity",
    formulaShort: "Energy + Clarity",
    cadence: "Monthly · 28-day",
    tenureMonths: 9,
    tenureLabel: "9 months",
    ltv: 711,
    nextRenewal: "Jun 14",
    score: 47,
    prevScore: 44,
    headline:
      "Results are landing — but he's reaching for the exits, price-checking hard after the renewal email hit his inbox.",
    factors: [
      { label: "Visited pricing page ×4", weight: 19, note: "After renewal email" },
      { label: "Coupon-site referral last login", weight: 17, note: "Active price shopping" },
      { label: "Opens steady, clicks ↓", weight: 6, note: "Engaged but hesitant" },
      { label: "On-time reorders ×8", weight: -12, note: "Strong habit signal" },
    ],
    action: {
      kind: "Plan reframe",
      title: "Show cost-per-day and the rate-lock annual plan — no blanket coupon",
      detail:
        "Reframe $79/mo as about $2.63/day and surface the annual plan that locks today's price. Lead with the value he's already getting, not a discount.",
      why:
        "Price-sensitive isn't unwilling to pay. A coupon resets his anchor permanently; a per-day reframe plus an annual rate-lock protects both margin and lifetime value.",
      effort: "Low touch · automated",
      cost: "Annual plan, no discount",
    },
    alternatives: ["10% loyalty credit at 12 months", "Downgrade to a single formula"],
    measure: {
      liftPts: 21, ci: 7, holdoutPct: 10, checkBack: "Jul 14",
      success: "Renews monthly or moves to annual",
      baseline: "Untreated price-shoppers churn at 27%",
    },
    message:
      "You've been running Energy + Clarity for nine months — long enough to know it works for you. If you'd rather lock today's pricing, the annual plan holds your rate and comes out to about $2.63 a day. Same formulas, same cadence.",
    judge: 4.2,
  },
  {
    id: "anita",
    archetype: "Product Overstock",
    archetypeKey: "overstock",
    name: "Anita Cho",
    initials: "AC",
    location: "San Jose, CA",
    formula: "Logic",
    formulaShort: "Logic",
    cadence: "Monthly · 28-day",
    tenureMonths: 11,
    tenureLabel: "11 months",
    ltv: 869,
    nextRenewal: "Jun 20",
    score: 39,
    prevScore: 31,
    headline:
      "Taking Logic about 4×/week, so monthly shipments are stacking up — surplus, not dissatisfaction.",
    factors: [
      { label: "Usage 4×/wk vs daily ship", weight: 18, note: "Self-reported in-app" },
      { label: "~2 unopened bottles (est.)", weight: 15, note: "Next ship would be 3rd" },
      { label: "Approaching reorder date", weight: 8, note: "Surplus before charge" },
      { label: "NPS still 8 / 10", weight: -9, note: "Likes it — just too much" },
    ],
    action: {
      kind: "Cadence adjustment",
      title: "Stretch to every 6 weeks to match real usage",
      detail:
        "Proactively offer a 45-day interval sized to how she actually takes Logic. Right-sizes spend before the pile-up itself becomes the reason she cancels.",
      why:
        "Overstock churn is a fit problem, not a value problem. Slowing delivery counterintuitively protects lifetime value versus losing her to a closet full of bottles.",
      effort: "Low touch · one-tap",
      cost: "Protects $79/mo",
    },
    alternatives: ["Skip next shipment only", "Switch to 90-count value size"],
    measure: {
      liftPts: 22, ci: 7, holdoutPct: 10, checkBack: "Aug 04",
      success: "Accepts 6-week cadence, keeps the plan",
      baseline: "Untreated overstock churns at 29%",
    },
    message:
      "Looks like Logic is lasting you longer than a month — no need to pay for bottles you're not getting to. Want to switch to every 6 weeks? It lines up with how you're actually taking it, and you can change it back anytime.",
    judge: 4.0,
  },
];

window.BELLWETHER = { FLEET, ARCHETYPES, SUBSCRIBERS, tierOf };

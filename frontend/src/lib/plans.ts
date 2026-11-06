export type PublicPlan = {
  id: string;
  name: string;
  tag: string;
  monthly: string;
  yearly: string;
  desc: string;
  features: string[];
  cta: string;
  href: string;
  highlight: boolean;
};

export const PUBLIC_PLANS: PublicPlan[] = [
  {
    id: "free",
    name: "Free",
    tag: "Always free",
    monthly: "₹0",
    yearly: "₹0",
    desc: "Get a feel for Okkra before committing.",
    features: [
      "3 sessions per month",
      "Text mode only",
      "Basic STAR feedback",
      "Readiness score",
    ],
    cta: "Start free",
    href: "/signup",
    highlight: false,
  },
  {
    id: "starter",
    name: "Starter",
    tag: "For freshers",
    monthly: "₹999",
    yearly: "₹9,999",
    desc: "Full access to practice. Right for freshers entering the market.",
    features: [
      "20 mock interviews per month",
      "Voice + Text modes",
      "Full STAR + filler analysis",
      "Readiness score & trend",
      "Resume visibility to recruiters",
    ],
    cta: "Start Starter",
    href: "/signup?plan=starter",
    highlight: false,
  },
  {
    id: "pro",
    name: "Pro",
    tag: "Most popular",
    monthly: "₹2,999",
    yearly: "₹29,999",
    desc: "For mid-level professionals stepping up or switching tracks.",
    features: [
      "40 mock interviews per month",
      "Everything in Starter",
      "Advanced feedback analytics",
      "Category performance tracking",
      "Priority recruiter discovery",
      "Drill recommendations",
    ],
    cta: "Start Pro",
    href: "/signup?plan=pro",
    highlight: true,
  },
  {
    id: "senior",
    name: "Senior",
    tag: "For leaders",
    monthly: "₹4,999",
    yearly: "₹49,999",
    desc: "For senior and leadership roles with elevated expectations.",
    features: [
      "100 mock interviews per month",
      "Everything in Pro",
      "Leadership interview formats",
      "Executive communication coaching",
      "Top recruiter priority listing",
      "Dedicated improvement path",
    ],
    cta: "Start Senior",
    href: "/signup?plan=senior",
    highlight: false,
  },
];

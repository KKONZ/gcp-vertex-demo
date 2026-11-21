# Fraud & Risk Indicator Playbook

These indicators are meant to be combined, not used individually — any single indicator
below is common among entirely legitimate customers, and should only shift a risk score
meaningfully when two or more co-occur on the same order.

- **Serial high-value returner**: return rate above 50% concentrated in the highest-price
  items of each order, while lower-priced items from the same orders are consistently
  kept. Suggests wardrobing rather than fit issues.
- **Address mismatch**: shipping and billing address differ, and the account was created
  within the last 30 days. Common in account-takeover and reshipping fraud.
- **Return velocity spike**: a customer's return rate in the last 30 days is more than
  double their lifetime average. Can indicate a recent bad experience worth a human
  follow-up, not automatically a fraud signal — route to review rather than auto-deny.
- **Cross-category consistency**: a customer with a high return rate concentrated in one
  category (e.g. always returning shoes, never returning accessories) is more likely
  experiencing a genuine fit/sizing problem than committing fraud. Fraud tends to be
  price-driven, not category-driven.

Recommended action mapping: zero or one indicator -> approve automatically. Two
indicators -> approve with a note for trend monitoring. Three or more, or any single
indicator combined with an address mismatch -> route to manual review before refunding.

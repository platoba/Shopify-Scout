"""Competitive pricing intelligence for Shopify stores.

Cross-store price comparison, price positioning analysis,
pricing strategy detection, and margin opportunity finder.
"""
import logging
import statistics
from typing import Optional
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)


class PricePoint:
    """Represents a single price observation."""

    def __init__(self, store: str, product_title: str, variant_title: str,
                 price: float, compare_at_price: float = 0,
                 product_type: str = "", vendor: str = "",
                 sku: str = "", product_id=None):
        self.store = store
        self.product_title = product_title
        self.variant_title = variant_title
        self.price = price
        self.compare_at_price = compare_at_price
        self.product_type = product_type
        self.vendor = vendor
        self.sku = sku
        self.product_id = product_id
        self.discount_pct = 0.0
        if compare_at_price and compare_at_price > price:
            self.discount_pct = round((1 - price / compare_at_price) * 100, 1)

    def to_dict(self) -> dict:
        return {
            "store": self.store,
            "product_title": self.product_title,
            "variant_title": self.variant_title,
            "price": self.price,
            "compare_at_price": self.compare_at_price,
            "discount_pct": self.discount_pct,
            "product_type": self.product_type,
            "vendor": self.vendor,
            "sku": self.sku,
        }


class PricingIntel:
    """Competitive pricing intelligence engine."""

    def __init__(self):
        self.price_points: list[PricePoint] = []

    def reset(self):
        self.price_points = []

    def load_store(self, store_name: str, products: list):
        """Load products from a store into the price database."""
        for p in products:
            product_type = p.get("product_type", "") or ""
            vendor = p.get("vendor", "") or ""
            title = p.get("title", "") or ""
            pid = p.get("id")

            for v in p.get("variants", []):
                try:
                    price = float(v.get("price", 0))
                except (ValueError, TypeError):
                    continue
                if price <= 0:
                    continue

                compare_at = 0
                try:
                    compare_at = float(v.get("compare_at_price", 0) or 0)
                except (ValueError, TypeError):
                    pass

                self.price_points.append(PricePoint(
                    store=store_name,
                    product_title=title,
                    variant_title=v.get("title", "Default"),
                    price=price,
                    compare_at_price=compare_at,
                    product_type=product_type,
                    vendor=vendor,
                    sku=v.get("sku", ""),
                    product_id=pid,
                ))

    def analyze_store(self, store_name: str) -> dict:
        """Analyze pricing for a single store."""
        store_prices = [pp for pp in self.price_points if pp.store == store_name]
        if not store_prices:
            return {"error": f"No data for store: {store_name}"}

        prices = [pp.price for pp in store_prices]
        discounted = [pp for pp in store_prices if pp.discount_pct > 0]

        return {
            "store": store_name,
            "total_variants": len(store_prices),
            "price_stats": self._calc_stats(prices),
            "pricing_strategy": self._detect_strategy(store_prices),
            "discount_analysis": {
                "discounted_items": len(discounted),
                "discount_rate": round(len(discounted) / len(store_prices) * 100, 1),
                "avg_discount": round(
                    statistics.mean([d.discount_pct for d in discounted]), 1
                ) if discounted else 0,
                "max_discount": max([d.discount_pct for d in discounted], default=0),
            },
            "price_tiers": self._analyze_tiers(prices),
            "category_pricing": self._by_category(store_prices),
        }

    def compare_stores(self, store_names: list[str] = None) -> dict:
        """Compare pricing across multiple stores."""
        if store_names is None:
            store_names = list(set(pp.store for pp in self.price_points))

        if len(store_names) < 2:
            return {"error": "Need at least 2 stores to compare"}

        store_analyses = {}
        for name in store_names:
            store_analyses[name] = self.analyze_store(name)

        # Build comparison matrix
        ranking = sorted(
            store_analyses.items(),
            key=lambda x: x[1].get("price_stats", {}).get("median", 0),
        )

        return {
            "stores": store_analyses,
            "price_ranking": [
                {
                    "rank": i + 1,
                    "store": name,
                    "median_price": data.get("price_stats", {}).get("median", 0),
                    "avg_price": data.get("price_stats", {}).get("mean", 0),
                    "position": self._price_position(
                        data.get("price_stats", {}).get("median", 0),
                        [s.get("price_stats", {}).get("median", 0) for _, s in ranking],
                    ),
                }
                for i, (name, data) in enumerate(ranking)
            ],
            "category_gaps": self._find_category_gaps(store_names),
            "opportunities": self._find_opportunities(store_analyses),
        }

    def find_similar_products(self, threshold: float = 0.8) -> list[dict]:
        """Find similar products across stores by title similarity."""
        from difflib import SequenceMatcher

        matches = []
        stores = list(set(pp.store for pp in self.price_points))

        # Group by store
        by_store = defaultdict(list)
        for pp in self.price_points:
            by_store[pp.store].append(pp)

        # Compare across stores
        for i, s1 in enumerate(stores):
            for s2 in stores[i + 1:]:
                for p1 in by_store[s1]:
                    for p2 in by_store[s2]:
                        sim = SequenceMatcher(
                            None,
                            p1.product_title.lower(),
                            p2.product_title.lower(),
                        ).ratio()
                        if sim >= threshold:
                            price_diff = p2.price - p1.price
                            price_diff_pct = round(
                                (price_diff / p1.price * 100) if p1.price > 0 else 0, 1
                            )
                            matches.append({
                                "store_a": s1,
                                "product_a": p1.product_title,
                                "price_a": p1.price,
                                "store_b": s2,
                                "product_b": p2.product_title,
                                "price_b": p2.price,
                                "similarity": round(sim, 3),
                                "price_diff": round(price_diff, 2),
                                "price_diff_pct": price_diff_pct,
                                "cheaper_store": s1 if p1.price < p2.price else s2,
                            })

        return sorted(matches, key=lambda x: abs(x["price_diff_pct"]), reverse=True)[:20]

    def _calc_stats(self, prices: list[float]) -> dict:
        """Calculate price statistics."""
        if not prices:
            return {}
        return {
            "min": round(min(prices), 2),
            "max": round(max(prices), 2),
            "mean": round(statistics.mean(prices), 2),
            "median": round(statistics.median(prices), 2),
            "stdev": round(statistics.stdev(prices), 2) if len(prices) > 1 else 0,
            "count": len(prices),
            "range": round(max(prices) - min(prices), 2),
        }

    def _detect_strategy(self, prices: list[PricePoint]) -> dict:
        """Detect the pricing strategy used by a store."""
        values = [pp.price for pp in prices]
        if not values:
            return {"type": "unknown"}

        median = statistics.median(values)
        mean = statistics.mean(values)
        stdev = statistics.stdev(values) if len(values) > 1 else 0

        # Charm pricing (prices ending in .99, .95)
        charm_count = sum(1 for v in values if str(v).endswith(("99", "95", ".99", ".95")))
        charm_pct = charm_count / len(values) * 100

        # Round pricing ($10, $20, $50)
        round_count = sum(1 for v in values if v == int(v) or v % 5 == 0)
        round_pct = round_count / len(values) * 100

        # Discount-heavy
        discount_count = sum(1 for pp in prices if pp.discount_pct > 0)
        discount_pct = discount_count / len(prices) * 100

        # Detect strategy type
        strategy_type = "mixed"
        if charm_pct > 60:
            strategy_type = "charm_pricing"
        elif round_pct > 60:
            strategy_type = "round_pricing"
        elif discount_pct > 50:
            strategy_type = "discount_heavy"
        elif stdev / mean < 0.3 if mean > 0 else False:
            strategy_type = "uniform_pricing"
        elif stdev / mean > 1.0 if mean > 0 else False:
            strategy_type = "wide_range"

        return {
            "type": strategy_type,
            "charm_pricing_pct": round(charm_pct, 1),
            "round_pricing_pct": round(round_pct, 1),
            "discount_heavy_pct": round(discount_pct, 1),
            "price_consistency": round(1 - (stdev / mean if mean > 0 else 0), 3),
        }

    def _analyze_tiers(self, prices: list[float]) -> dict:
        """Analyze price distribution into tiers."""
        if not prices:
            return {}

        tiers = {
            "budget": {"range": "$0-25", "min": 0, "max": 25, "count": 0},
            "mid_range": {"range": "$25-75", "min": 25, "max": 75, "count": 0},
            "premium": {"range": "$75-200", "min": 75, "max": 200, "count": 0},
            "luxury": {"range": "$200+", "min": 200, "max": float("inf"), "count": 0},
        }

        for p in prices:
            for tier_data in tiers.values():
                if tier_data["min"] <= p < tier_data["max"]:
                    tier_data["count"] += 1
                    break

        total = len(prices)
        for tier_data in tiers.values():
            tier_data["pct"] = round(tier_data["count"] / total * 100, 1)
            del tier_data["min"]
            del tier_data["max"]

        # Find dominant tier
        dominant = max(tiers.items(), key=lambda x: x[1]["count"])
        return {
            "tiers": tiers,
            "dominant_tier": dominant[0],
            "dominant_pct": dominant[1]["pct"],
        }

    def _by_category(self, prices: list[PricePoint]) -> dict:
        """Analyze pricing by product category."""
        by_cat = defaultdict(list)
        for pp in prices:
            cat = pp.product_type or "Other"
            by_cat[cat].append(pp.price)

        result = {}
        for cat, cat_prices in sorted(by_cat.items(), key=lambda x: -len(x[1])):
            result[cat] = {
                "count": len(cat_prices),
                "avg_price": round(statistics.mean(cat_prices), 2),
                "min": round(min(cat_prices), 2),
                "max": round(max(cat_prices), 2),
            }
        return result

    def _price_position(self, median: float, all_medians: list[float]) -> str:
        """Determine price position relative to competitors."""
        if not all_medians or len(all_medians) < 2:
            return "only_store"
        overall_median = statistics.median(all_medians)
        if median < overall_median * 0.85:
            return "budget"
        elif median > overall_median * 1.15:
            return "premium"
        else:
            return "mid_market"

    def _find_category_gaps(self, store_names: list[str]) -> list[dict]:
        """Find categories that some stores have but others don't."""
        by_store_cat = defaultdict(set)
        for pp in self.price_points:
            if pp.store in store_names and pp.product_type:
                by_store_cat[pp.store].add(pp.product_type)

        all_cats = set()
        for cats in by_store_cat.values():
            all_cats.update(cats)

        gaps = []
        for cat in all_cats:
            stores_with = [s for s in store_names if cat in by_store_cat.get(s, set())]
            stores_without = [s for s in store_names if cat not in by_store_cat.get(s, set())]
            if stores_without and stores_with:
                gaps.append({
                    "category": cat,
                    "available_in": stores_with,
                    "missing_from": stores_without,
                    "opportunity": f"Expand into '{cat}' category",
                })

        return sorted(gaps, key=lambda x: len(x["missing_from"]), reverse=True)[:10]

    def _find_opportunities(self, analyses: dict) -> list[str]:
        """Find pricing opportunities across competitors."""
        opps = []
        discount_rates = {
            name: data.get("discount_analysis", {}).get("discount_rate", 0)
            for name, data in analyses.items()
        }

        # Store with fewest discounts might be premium-positioned
        if discount_rates:
            min_disc = min(discount_rates, key=discount_rates.get)
            max_disc = max(discount_rates, key=discount_rates.get)
            if discount_rates[max_disc] > 40:
                opps.append(
                    f"⚠️ {max_disc} discounts {discount_rates[max_disc]:.0f}% of items "
                    f"— may be eroding brand value"
                )
            if discount_rates[min_disc] < 5:
                opps.append(
                    f"💎 {min_disc} rarely discounts ({discount_rates[min_disc]:.0f}%) "
                    f"— strong brand pricing power"
                )

        # Compare median prices
        medians = {
            name: data.get("price_stats", {}).get("median", 0)
            for name, data in analyses.items()
        }
        if medians:
            cheapest = min(medians, key=medians.get)
            priciest = max(medians, key=medians.get)
            if medians[priciest] > 0:
                ratio = medians[priciest] / max(medians[cheapest], 0.01)
                if ratio > 2:
                    opps.append(
                        f"📊 {ratio:.1f}x price gap between {cheapest} "
                        f"(${medians[cheapest]:.0f}) and {priciest} "
                        f"(${medians[priciest]:.0f})"
                    )

        return opps


def analyze_pricing(store_name: str, products: list) -> dict:
    """Convenience function for single-store pricing analysis."""
    intel = PricingIntel()
    intel.load_store(store_name, products)
    return intel.analyze_store(store_name)

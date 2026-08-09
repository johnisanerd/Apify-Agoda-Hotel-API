"""Agoda Hotel API: a quick-start example in Python.

See more at: https://apify.com/johnvc/agoda-hotel-api?fpr=9n7kx3
Input schema: https://apify.com/johnvc/agoda-hotel-api/input-schema?fpr=9n7kx3

This script calls the Agoda Hotel API on Apify and reads its structured JSON
output. The headline field is `roomRates`: one entry per bookable offer, each
carrying `pricePerNight` next to `originalPricePerNight` (the pre-discount rate)
plus the cancellation `policies` for that offer.

Dates are required in search mode, because a room rate only exists for a
specific stay. Every recipe below computes its stay dates relative to today, so
the examples never go stale and never ask for a date in the past.

Get your free Apify API key at: https://apify.com?fpr=9n7kx3

Examples:
  uv run python agoda-hotel-api-example.py
  uv run python agoda-hotel-api-example.py --example rate-watch
  uv run python agoda-hotel-api-example.py --example free-cancellation
  uv run python agoda-hotel-api-example.py --example property-detail
  uv run python agoda-hotel-api-example.py --example reviews
"""

from __future__ import annotations

import argparse
import os
from datetime import date, timedelta
from typing import Any

from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv()

ACTOR_ID = "johnvc/agoda-hotel-api"

# A stay far enough ahead that it is always bookable. Computed from today, so
# this file does not rot and no example ever asks for a date in the past.
LEAD_DAYS = 45
NIGHTS = 3

# Used by the property-detail and reviews recipes. Swap in any Agoda property URL.
SAMPLE_HOTEL_URL = "https://www.agoda.com/marina-bay-sands/hotel/singapore-sg.html"


def stay_dates(lead_days: int = LEAD_DAYS, nights: int = NIGHTS) -> tuple[str, str]:
    """Return (checkIn, checkOut) as YYYY-MM-DD strings, relative to today.

    Args:
        lead_days: How many days from today the stay starts.
        nights: How many nights the stay runs for.

    Returns:
        A tuple of ISO date strings suitable for `checkIn` and `checkOut`.
    """
    check_in = date.today() + timedelta(days=lead_days)
    return check_in.isoformat(), (check_in + timedelta(days=nights)).isoformat()


def fetch(client: ApifyClient, run_input: dict[str, Any]) -> list[dict[str, Any]]:
    """Run the Actor and return every row from its default dataset.

    apify-client 3.x returns a typed `Run` object, so read `default_dataset_id`
    as an attribute rather than a dict key.
    """
    run = client.actor(ACTOR_ID).call(run_input=run_input)
    if run is None:
        raise SystemExit("The Actor run did not return a result.")
    print(f"Run {run.id} finished with status {run.status}.")
    return list(client.dataset(run.default_dataset_id).iterate_items())


def cheapest_offer(item: dict[str, Any]) -> dict[str, Any] | None:
    """Pick the lowest-priced entry from a property's `roomRates` table."""
    offers = [o for o in (item.get("roomRates") or []) if o.get("pricePerNight") is not None]
    return min(offers, key=lambda o: o["pricePerNight"]) if offers else None


def print_properties(items: list[dict[str, Any]]) -> None:
    """Print the rate-monitoring fields from every property row."""
    properties = [i for i in items if i.get("result_type") == "property"]
    errors = [i for i in items if i.get("result_type") == "error"]
    print(f"Returned {len(properties)} property row(s) and {len(errors)} error row(s).\n")

    for item in properties:
        currency = item.get("currency", "")
        print(f"{item.get('propertyName')} ({item.get('city')}, {item.get('country')})")
        print(f"  Rate window: {str(item.get('checkIn'))[:10]} to {str(item.get('checkOut'))[:10]}")
        print(f"  Available:   {item.get('available')}")
        print(f"  From:        {item.get('lowestPricePerNight')} {currency} per night")
        print(f"  Guest score: {item.get('reviewScore')} from {item.get('reviewCount')} reviews")

        breakdown = item.get("reviewScoreBreakdown") or {}
        if breakdown:
            parts = ", ".join(f"{k}={v}" for k, v in list(breakdown.items())[:6])
            print(f"  Breakdown:   {parts}")

        offers = item.get("roomRates") or []
        print(f"  Offers:      {len(offers)} bookable rate(s)")
        best = cheapest_offer(item)
        if best:
            saving = ""
            original = best.get("originalPricePerNight")
            if original and best.get("pricePerNight"):
                saving = f" (was {original}, a {round(100 * (1 - best['pricePerNight'] / original))}% cut)"
            print(f"    - {best.get('roomType')}: {best.get('pricePerNight')} {best.get('currency', currency)}{saving}")
            print(f"      Nights: {best.get('nights')} | Beds: {best.get('bedConfiguration')} | Taxes included: {best.get('taxesAndFeesIncluded')}")
            print(f"      Policies: {', '.join(best.get('policies') or []) or 'not stated'}")
        print(f"  URL:         {item.get('propertyUrl')}")
        print()

    for err in errors:
        print(f"Error on {err.get('sourceInput')}: {err.get('error_message')}")


def run_default(client: ApifyClient) -> None:
    """Cheap general quick-start: one destination, a handful of properties.

    Inputs are kept small (one destination, maxResultsPerInput=3) to keep this
    first run inexpensive. You are billed per result returned, so raise
    maxResultsPerInput only once you know your budget.
    """
    check_in, check_out = stay_dates()
    run_input: dict[str, Any] = {
        "mode": "search",
        "locations": ["Singapore"],
        "checkIn": check_in,
        "checkOut": check_out,
        "adults": 2,
        "currency": "USD",
        "country": "US",
        "maxResultsPerInput": 3,
    }
    print(f"Searching Singapore for a {NIGHTS}-night stay from {check_in} to {check_out}.\n")
    print_properties(fetch(client, run_input))


def run_rate_watch(client: ApifyClient) -> None:
    """Rate monitor: one line per property, ready to append to a CSV and diff.

    Run this on a schedule with the same destination and dates, then compare
    `lowestPricePerNight` between runs to see prices move. Fix `currency` and
    `country` so every snapshot is quoted in the same terms.
    """
    check_in, check_out = stay_dates(lead_days=60, nights=3)
    run_input: dict[str, Any] = {
        "mode": "search",
        "locations": ["Bangkok"],
        "checkIn": check_in,
        "checkOut": check_out,
        "adults": 2,
        "currency": "USD",
        "country": "US",
        "maxResultsPerInput": 3,
    }
    items = fetch(client, run_input)
    print("\ncaptured_at,property,check_in,check_out,currency,lowest_price_per_night,available")
    for item in items:
        if item.get("result_type") != "property":
            continue
        name = str(item.get("propertyName", "")).replace(",", " ")
        print(
            f"{item.get('fetched_at')},{name},{str(item.get('checkIn'))[:10]},"
            f"{str(item.get('checkOut'))[:10]},{item.get('currency')},"
            f"{item.get('lowestPricePerNight')},{item.get('available')}"
        )


def run_free_cancellation(client: ApifyClient) -> None:
    """Keep only the offers you can cancel, using the per-offer `policies` list.

    The API returns every bookable offer with its cancellation terms attached,
    so refundable and non-refundable rates are separable client side.
    """
    check_in, check_out = stay_dates(lead_days=50, nights=2)
    run_input: dict[str, Any] = {
        "mode": "search",
        "locations": ["Tokyo"],
        "checkIn": check_in,
        "checkOut": check_out,
        "adults": 2,
        "currency": "USD",
        "country": "US",
        "maxResultsPerInput": 3,
    }
    items = fetch(client, run_input)
    for item in items:
        if item.get("result_type") != "property":
            continue
        refundable = [
            offer
            for offer in (item.get("roomRates") or [])
            if any("cancel" in str(p).lower() for p in (offer.get("policies") or []))
            and not any("non-refundable" in str(p).lower() for p in (offer.get("policies") or []))
        ]
        print(f"\n{item.get('propertyName')}: {len(refundable)} cancellable offer(s)")
        for offer in refundable[:3]:
            print(
                f"  {offer.get('roomType')}: {offer.get('pricePerNight')} "
                f"{offer.get('currency')} per night | {', '.join(offer.get('policies') or [])}"
            )


def run_property_detail(client: ApifyClient) -> None:
    """Property mode: full detail from hotel URLs, no dates needed.

    Property mode collects the description, facilities, location signals, and
    guest scores for a URL you already have. It carries no rate table, because
    rates only exist for a specific stay: use search mode for pricing.
    """
    run_input: dict[str, Any] = {
        "mode": "property",
        "hotelUrls": [SAMPLE_HOTEL_URL],
        "maxResultsPerInput": 1,
    }
    for item in fetch(client, run_input):
        if item.get("result_type") != "property":
            print(item)
            continue
        print(f"\n{item.get('propertyName')}")
        print(f"  Address:   {item.get('location')}")
        print(f"  Coords:    {item.get('latitude')}, {item.get('longitude')}")
        print(f"  Score:     {item.get('reviewScore')} from {item.get('reviewCount')} reviews")
        print(f"  Location:  {item.get('locationRating')} ({item.get('locationRatingLabel')})")
        print(f"  Popular:   {', '.join((item.get('popularFacilities') or [])[:5])}")
        # `whatsNearby` arrives as groups, each with a name and a list of places.
        for group in (item.get("whatsNearby") or [])[:2]:
            places = group.get("value") if isinstance(group, dict) else None
            label = group.get("name") if isinstance(group, dict) else str(group)
            print(f"  {label}: {', '.join(str(p) for p in (places or [])[:5])}")
        print(f"  Summary:   {item.get('summary')}")


def run_reviews(client: ApifyClient) -> None:
    """Reviews mode: guest reviews for a hotel URL.

    Every review carries `rating`, `authorName`, `reviewDate`, `nightsStayed`,
    and `reviewLanguage`, plus the property's own score and score breakdown.
    Where the source splits a review into a liked half and a disliked half, you
    also get `reviewPositive` and `reviewNegative`, and `ownerReply` when the
    property replied. Those three are not on every review, so they are printed
    only when present.

    Reviews are slower than search, so allow several minutes per batch, and keep
    maxResultsPerInput low while you are testing. You are billed per review.
    """
    run_input: dict[str, Any] = {
        "mode": "reviews",
        "hotelUrls": [SAMPLE_HOTEL_URL],
        "maxResultsPerInput": 3,
    }
    for item in fetch(client, run_input):
        if item.get("result_type") != "review":
            print(item)
            continue
        print(f"\n{item.get('authorName')} rated {item.get('rating')} on {str(item.get('reviewDate'))[:10]}")
        print(f"  Property: {item.get('propertyName')} ({item.get('propertyLocation')})")
        print(f"  Overall:  {item.get('propertyReviewScore')} from {item.get('propertyReviewCount')} reviews")
        print(f"  Nights:   {item.get('nightsStayed')} | Language: {item.get('reviewLanguage')}")
        if item.get("reviewPositive"):
            print(f"  Liked:    {item['reviewPositive']}")
        if item.get("reviewNegative"):
            print(f"  Disliked: {item['reviewNegative']}")
        if item.get("ownerReply"):
            print(f"  Reply:    {item['ownerReply'][:160]}")


def main() -> None:
    """Dispatch one of the recipes described in the README."""
    dispatch = {
        "default": run_default,
        "rate-watch": run_rate_watch,
        "free-cancellation": run_free_cancellation,
        "property-detail": run_property_detail,
        "reviews": run_reviews,
    }

    parser = argparse.ArgumentParser(description="Agoda Hotel API examples")
    parser.add_argument(
        "--example",
        default="default",
        choices=list(dispatch),
        help="Which recipe to run (see the README Recipes section).",
    )
    args = parser.parse_args()

    token = os.getenv("APIFY_API_TOKEN")
    if not token:
        raise SystemExit(
            "Set APIFY_API_TOKEN in .env or the environment. "
            "Get a free key at https://apify.com?fpr=9n7kx3"
        )

    dispatch[args.example](ApifyClient(token))


if __name__ == "__main__":
    main()

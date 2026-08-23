# 🏨 Agoda Hotel API: an Agoda API for live room rates, availability, and hotel reviews

> The unofficial Agoda API that returns live per-room rates for a specific stay, with the pre-discount price sitting next to the price you would actually pay, and the cancellation terms attached to every offer.

**Actor page:** [apify.com/johnvc/agoda-hotel-api](https://apify.com/johnvc/agoda-hotel-api?fpr=9n7kx3)
**Input schema:** [apify.com/johnvc/agoda-hotel-api/input-schema](https://apify.com/johnvc/agoda-hotel-api/input-schema?fpr=9n7kx3)

Agoda gates its own developer API behind a partner programme, so most people searching for an Agoda API end up with nothing they can call. This repo shows how to use the Agoda Hotel API on Apify instead: give it a destination and a check-in and check-out date, and it returns each property as structured JSON with a full `roomRates` table, a `lowestPricePerNight` lifted to the top of the record, an `available` flag, and the guest score plus its `reviewScoreBreakdown`. A second mode pulls hotel reviews from property URLs, one row per review, with what the guest liked and what they disliked kept as separate fields wherever the source splits them that way. Everything here runs from Python with `uv`, or from Claude, Cursor, and ChatGPT over MCP.

## Video Walkthrough

[![Watch the walkthrough](https://img.youtube.com/vi/jREWahDGhJM/maxresdefault.jpg)](https://www.youtube.com/watch?v=jREWahDGhJM)

### Text walkthrough

The Agoda API in this repo has three modes, and `search` is the one that carries pricing. You pass `locations` (up to 20 destinations, cities or regions or landmarks), a `checkIn` and `checkOut` date as `YYYY-MM-DD`, the number of `adults`, and optionally a `currency` and a point-of-sale `country`. Dates are required, and that is deliberate: a hotel does not have one price, it has a price for a set of nights at a given occupancy, so a dateless search has no meaningful answer. Each property comes back with `roomRates`, one entry per bookable offer, each carrying `roomType`, `bedConfiguration`, `pricePerNight`, `originalPricePerNight`, `taxesAndFeesIncluded`, `nights`, and a `policies` list that tells you whether the rate is refundable. The cheapest offer is lifted into `lowestPricePerNight` so a rate monitor can diff a single number between runs instead of walking the whole tree. The other two modes take `hotelUrls`: `property` returns the full property record (description, facilities, coordinates, location rating), and `reviews` returns guest reviews, which is what you want when an OTA rate monitoring dashboard needs sentiment next to price. A typical job is a scheduled run over one destination and a fixed stay, appending `lowestPricePerNight` to a table each morning so you can see rates move. Every example in this repo computes its stay dates relative to today, so nothing here asks for a date in the past.

## Quick Start

### Prerequisites
- Python 3.11 or higher
- An Apify account and API key ([get a free key here](https://apify.com?fpr=9n7kx3))

1. **Clone the repository**
   ```bash
   git clone https://github.com/johnisanerd/Apify-Agoda-Hotel-API.git
   cd Apify-Agoda-Hotel-API
   ```

2. **Install dependencies with UV**
   ```bash
   # Install UV if you do not have it:
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Install project dependencies:
   uv sync
   ```

3. **Configure your API key**
   ```bash
   cp .env.example .env
   # Edit .env and add your Apify API key
   # Get your free API key at: https://apify.com?fpr=9n7kx3
   ```

4. **Run the example**
   ```bash
   uv run python agoda-hotel-api-example.py

   # Or pick a recipe:
   uv run python agoda-hotel-api-example.py --example rate-watch
   uv run python agoda-hotel-api-example.py --example free-cancellation
   uv run python agoda-hotel-api-example.py --example property-detail
   uv run python agoda-hotel-api-example.py --example reviews
   ```

### Alternative: set the API key directly
```bash
export APIFY_API_TOKEN="your_api_key_here"
uv run python agoda-hotel-api-example.py
```

The default run searches one destination for three properties on a stay 45 days out. Billing is per result returned, so `maxResultsPerInput` is your cost dial: it is set to `3` in every example on purpose, and you should raise it only once you know your budget.

## Why Use This Agoda API?

**You get the rate, not just the listing.** Plenty of hotel data sources will hand you a name, an address, and a star rating. This one returns the offer table for a real stay: every bookable room with its nightly price, the tax position, and the cancellation terms. That is the difference between a directory and something you can build a pricing product on.

**Both prices, side by side.** Each offer carries `pricePerNight` and `originalPricePerNight`. The gap between them is the advertised saving, so you can measure how deep a discount really is instead of taking the badge at face value.

**Cancellation terms are per offer, not per hotel.** The `policies` list sits inside each `roomRates` entry, so refundable and non-refundable rates are separable client side. The `free-cancellation` recipe in this repo does exactly that with one list comprehension.

**One number to diff.** `lowestPricePerNight` is the cheapest offer across every room, lifted to the top level. A scheduled OTA rate monitoring job can compare that single field between runs and only dig into `roomRates` when it moves.

**Hotel reviews as structured rows.** Reviews mode gives you one row per guest review with `rating`, `authorName`, `reviewDate`, `nightsStayed`, and `reviewLanguage`, plus the property's own `propertyReviewScore` and `propertyScoreBreakdown` on every row. Where the source splits a review into what the guest liked and what they disliked, you also get `reviewPositive` and `reviewNegative` as separate fields instead of one blob of text. Property records carry `reviewScore`, `reviewCount`, and a `reviewScoreBreakdown` across cleanliness, comfort, location, facilities, staff, and value for money.

**No key to beg for.** You do not apply to a partner programme. You bring an Apify token and call it from Python, from a scheduled task, or from an MCP client.

## Features

### Core Capabilities
- Three modes in one Actor: `search` (destination plus dates, returns live rates), `property` (full detail from hotel URLs), and `reviews` (guest reviews from hotel URLs)
- Up to 20 destinations or 200 hotel URLs per run
- Rates quoted in the `currency` and point-of-sale `country` you choose, so cross-market comparisons are like for like
- `adults` occupancy is part of the query, because occupancy changes the rate
- `maxResultsPerInput` caps properties per destination or reviews per hotel, and doubles as the cost control
- Results push in chunks as they complete, so rows arrive during the run rather than all at the end

### Data Quality
- Every row carries a `result_type` of `property`, `review`, or `error`, so partial failures never look like missing data
- Inputs that return nothing produce an explicit error row with a plain-language `error_message`
- Dates are validated before anything is sent upstream, so a bad stay window fails in seconds instead of hanging
- Every row carries `fetched_at`, a UTC timestamp, which is what makes a time series out of repeated runs
- Property and review rows both include a one-line plain-language `summary`

## Recipes

Each recipe is a named function in `agoda-hotel-api-example.py`. All of them keep `maxResultsPerInput` at 3 or less and compute stay dates from today.

### Track hotel prices for a destination and dates

```bash
uv run python agoda-hotel-api-example.py --example rate-watch
```

Searches one destination for a fixed stay with `currency` and `country` pinned, then prints one CSV line per property: `fetched_at`, name, stay window, currency, `lowestPricePerNight`, `available`. Append that to a file on a schedule and you have a price history.

### Find rates you can actually cancel

```bash
uv run python agoda-hotel-api-example.py --example free-cancellation
```

Runs a search, then filters each property's `roomRates` down to offers whose `policies` mention free cancellation, dropping anything marked non-refundable. Prints the room type, nightly price, and the exact policy text with its cancel-by date.

### Pull the full property record

```bash
uv run python agoda-hotel-api-example.py --example property-detail
```

Property mode takes `hotelUrls` and needs no dates. You get the address, coordinates, description, `popularFacilities`, `locationRating` and its label, and the `whatsNearby` groups. There is no rate table in this mode, because rates only exist for a specific stay.

### Collect hotel reviews for a property

```bash
uv run python agoda-hotel-api-example.py --example reviews
```

Reviews mode returns one row per guest review with `rating`, `authorName`, `reviewDate`, `nightsStayed`, and `reviewLanguage`, alongside the property's own score and breakdown. Where the source splits the review, `reviewPositive` and `reviewNegative` come through as separate fields, and `ownerReply` appears where the property replied. Reviews are slower than search, so allow several minutes per batch and keep `maxResultsPerInput` low while testing.

**Schedule tip:** save any of these inputs as an Apify Task and [schedule it](https://apify.com/johnvc/agoda-hotel-api?fpr=9n7kx3) to run daily or weekly. Rate monitoring is only useful as a series, and a scheduled task means the dataset keeps growing without anyone touching it.

## Usage Examples

### Basic Example
```json
{
  "mode": "search",
  "locations": ["Singapore"],
  "checkIn": "2027-03-14",
  "checkOut": "2027-03-17",
  "adults": 2,
  "currency": "USD",
  "country": "US",
  "maxResultsPerInput": 3
}
```

### Advanced Example
```json
{
  "mode": "search",
  "locations": ["Bangkok", "Tokyo", "Seoul"],
  "checkIn": "2027-03-14",
  "checkOut": "2027-03-19",
  "adults": 2,
  "currency": "EUR",
  "country": "DE",
  "maxResultsPerInput": 25
}
```

### Reviews Example
```json
{
  "mode": "reviews",
  "hotelUrls": [
    "https://www.agoda.com/village-hotel-bugis/hotel/singapore-sg.html"
  ],
  "maxResultsPerInput": 50
}
```

Replace the dates above with dates in your own future. Rates exist only for a stay that has not happened yet, so a check-in in the past returns nothing useful.

## Input Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `mode` | `str` | YES | `search` | `search` finds properties with live room rates from a destination and dates. `property` collects full detail from hotel URLs. `reviews` collects guest reviews from hotel URLs. |
| `locations` | `list[str]` | in search mode | `["Singapore"]` | Cities, regions, or landmarks to search. Up to 20 per run. |
| `checkIn` | `str` | in search mode | `2026-09-15` | Check-in date as `YYYY-MM-DD`. Room rates only exist for a specific stay. |
| `checkOut` | `str` | in search mode | `2026-09-18` | Check-out date as `YYYY-MM-DD`, later than check-in. |
| `adults` | `int` | no | `2` | Number of adults, which changes the rates returned. Range 1 to 20. |
| `currency` | `str` | no | source default | Three-letter currency code for the rates, for example `USD` or `EUR`. |
| `country` | `str` | no | source default | Two-letter country code for the point of sale. Rates can differ by market, so set this when comparing like for like. |
| `hotelUrls` | `list[str]` | in property and reviews modes | - | Agoda property URLs. Up to 200 per run. |
| `maxResultsPerInput` | `int` | no | `20` | Properties per destination in search mode, or reviews per hotel in reviews mode. Range 1 to 2000. You are charged per result returned, so this is also your cost control. |
| `sortReviewsBy` | `str` | no | source default | Optional sort order for reviews mode, passed through to the source, for example `Most recent`. |

## Output Format

A real property row from a search run, trimmed for length. Long arrays are shown with a single element.

```json
{
  "result_type": "property",
  "propertyId": "254056",
  "propertyName": "V Hotel Lavender",
  "propertyUrl": "https://www.agoda.com/v-hotel-lavender/hotel/singapore-sg.html",
  "location": "70 Jellicoe Road, Kallang, Singapore, Singapore, 208767",
  "city": "Singapore",
  "country": "Singapore",
  "latitude": 1.3078066110610962,
  "longitude": 103.86276245117188,
  "checkIn": "2026-09-22T00:00:00.000Z",
  "checkOut": "2026-09-30T00:00:00.000Z",
  "available": true,
  "lowestPricePerNight": 92.21,
  "currency": "USD",
  "roomRates": [
    {
      "roomType": "Superior Twin",
      "bedConfiguration": "2 single beds",
      "adults": 2,
      "children": 0,
      "pricePerNight": 92.21,
      "originalPricePerNight": 323.51,
      "currency": "USD",
      "taxesAndFeesIncluded": true,
      "nights": 8,
      "policies": [
        "Non-refundable (Low price!)",
        "Book and pay now",
        "Free WiFi",
        "Limited Time Offer. Price includes 15% discount!"
      ]
    }
  ],
  "roomsAvailable": [
    { "roomType": "Superior Twin", "roomSize": "14 m²/151 ft²", "beds": "2 single beds" }
  ],
  "reviewScore": 7.9,
  "reviewCount": 66927,
  "reviewScoreBreakdown": {
    "cleanliness": 7.9, "comfort": 7.9, "location": 9.1,
    "facilities": 7.6, "staff": 7.8, "value_for_money": 7.8
  },
  "locationRating": 9.1,
  "locationRatingLabel": "Exceptional",
  "propertyHighlights": ["Ideal location", "Great swimming pool", "Top value"],
  "popularFacilities": ["Free Wi-Fi ", "Swimming pool", "Car park"],
  "whatsNearby": [
    { "name": "Popular landmarks", "value": ["Singapore Flyer", "Gardens By The Bay"] }
  ],
  "walkablePlaces": [{ "name": "Seven eleven - 7-11", "value": "0.04" }],
  "images": ["https://pix8.agoda.net/hotelImages/254056/-1/3a2de50482d1ce38dd0aed52bf5ba03b.jpg"],
  "finePrint": "Distances shown are straight-line distances on the map.",
  "summary": "V Hotel Lavender in Singapore. Scored 7.9 from 66,927 reviews, from usd 92.21 per night.",
  "fetched_at": "2026-08-09T01:01:40.910640+00:00"
}
```

A real review row from a reviews run:

```json
{
  "result_type": "review",
  "reviewId": "578078942",
  "propertyId": "185945",
  "propertyName": "Marina Bay Sands",
  "propertyLocation": "10 Bayfront Avenue, Marina Bay, Singapore, Singapore, 018956",
  "propertyType": "Hotel",
  "propertyStarRating": 5,
  "propertyReviewScore": 8.8,
  "propertyReviewCount": 35400,
  "propertyScoreBreakdown": {
    "cleanliness": 9.3, "location": 9.2, "service": 9,
    "value_for_money": 8, "comfort": 8.6
  },
  "rating": 7.6,
  "reviewDate": "2022-12-17T04:49:00.000Z",
  "reviewLanguage": "en",
  "authorName": "Sheena",
  "nightsStayed": 1,
  "summary": "7.6-out-of-10 review of Marina Bay Sands by Sheena after 1 night(s).",
  "fetched_at": "2026-08-09T01:16:42.269032+00:00"
}
```

Notes on reading the output. Fields are omitted rather than set to null when the source has nothing, so use `.get()` in Python and expect gaps rather than assuming every key is present. On a property row, `checkIn` and `checkOut` are the stay window the source quoted these offers for, and each offer carries its own `nights` count, so read `nights` when you need the length of stay a price applies to. `whatsNearby`, `walkablePlaces`, `amenities`, and `faq` arrive as lists of `{name, value}` groups rather than flat lists of strings. On a review row, `reviewPositive`, `reviewNegative`, and `ownerReply` appear only where the source splits the review that way or the property replied, and plenty of reviews carry none of the three, so treat them as optional and lean on `rating`, `reviewDate`, and `nightsStayed` for anything you need on every row. An input that returns nothing produces a row with `result_type` of `error` and a readable `error_message`, which is also what you get if a single property's pages are temporarily unreadable while the rest of the batch succeeds.

## People also search for

### Is this an Agoda scraper or an API?

Both descriptions get used. People search for an Agoda scraper when what they want is programmatic access to hotel prices and reviews; this repo teaches the **Agoda Hotel API** on Apify, which returns structured JSON you can call from Python, from a scheduled task, or over MCP. There is no HTML parsing on your side.

### How do I use the Agoda API from Python?

Clone this repo, run `uv sync`, put your Apify token in `.env`, and run `uv run python agoda-hotel-api-example.py`. The call is three lines with the Apify client: build a `run_input` dict, call `client.actor("johnvc/agoda-hotel-api").call(run_input=run_input)`, then iterate `client.dataset(run.default_dataset_id).iterate_items()`. See Quick Start above.

### How do I track hotel prices over time?

Run search mode on a schedule with the same destination, dates, `currency`, and `country`, then compare `lowestPricePerNight` between runs. Every row carries `fetched_at`, so appending each run to one dataset gives you a price series without extra bookkeeping. The `rate-watch` recipe prints rows in exactly that shape.

### How do I compare hotel rates across booking sites?

Pin `currency` and `country` explicitly so both sides of the comparison are quoted in the same terms, and compare the same stay window and occupancy. Then match on property name and city, or on coordinates, since property IDs differ between sites. For the other half of the comparison, the [Google Hotels API](https://apify.com/johnvc/google-hotels-search-scraper?fpr=9n7kx3) covers aggregated hotel prices.

### How do I get hotel availability programmatically?

Every property row carries an `available` boolean for the stay you asked about, alongside `roomsAvailable` and the `roomRates` offer table. A property with `available` true and an empty rate table is sold out for that occupancy, which is worth checking separately when you are monitoring availability rather than price.

### Can I get hotel reviews and rates in one run?

Not in one run. Rates come from `search` mode and hotel reviews come from `reviews` mode. Run search first, take `propertyUrl` from the results, and feed those into a reviews run.

### Can I run this with MCP or Claude?

Yes. Use the install sections below to add the Actor as an MCP tool in [Claude Code](https://claude.ai/referral/uIlpa7nPLg) (free trial), [Claude Cowork](https://claude.ai/referral/uIlpa7nPLg) (free trial), Claude on the web, Cursor, or ChatGPT, then ask in plain language for the cheapest refundable rate in a city for your dates.

### Does the price include taxes and fees?

Each offer says so in `taxesAndFeesIncluded`. Do not assume it is consistent across the offers on one property, because it is not.

---

## Install in Claude Cowork Desktop

![Install in Claude Cowork Desktop](https://raw.githubusercontent.com/johnisanerd/ApifyPublicData/main/assets/guides/install_mcp_into_claude_desktop.png)

Cowork is the desktop app's automation mode. To give it the Agoda Hotel API as a tool, add the Apify MCP server as a connector.

1. Open the Claude desktop app and go to **Settings → Connectors** (or **Settings → Developer → Edit Config** to edit `claude_desktop_config.json` directly).
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
2. Add the Apify MCP server, preloaded with only this Actor:

```json
{
  "mcpServers": {
    "apify": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "https://mcp.apify.com/?tools=actors,docs,johnvc/agoda-hotel-api"
      ]
    }
  }
}
```

3. Restart the app. When Cowork first calls the tool, complete the OAuth prompt in your browser, or add your Apify API token in the connector settings to skip OAuth.
4. In a Cowork chat, confirm the tool is available and ask it to run the Agoda Hotel API.

Download the desktop app and start a free trial: https://claude.ai/referral/uIlpa7nPLg
More help: https://docs.apify.com/platform/integrations/claude-desktop

---

## Install in Claude Code

![Install in Claude Code](https://raw.githubusercontent.com/johnisanerd/ApifyPublicData/main/assets/guides/install_mcp_into_claude_code.png)

Claude Code is the command-line tool. Add the Actor's MCP server with one command:

```bash
claude mcp add --transport http apify \
  "https://mcp.apify.com/?tools=actors,docs,johnvc/agoda-hotel-api"
```

To use a token instead of browser OAuth:

```bash
claude mcp add --transport http apify \
  "https://mcp.apify.com/?tools=actors,docs,johnvc/agoda-hotel-api" \
  --header "Authorization: Bearer YOUR_APIFY_TOKEN"
```

Then verify with `claude mcp list`, or run `/mcp` inside a session. Ask Claude Code to call the Agoda Hotel API.

Try Claude Code free: https://claude.ai/referral/uIlpa7nPLg
Claude Code MCP docs: https://code.claude.com/docs/en/mcp

---

## Install in Claude (website)

![Install in Claude (website)](https://raw.githubusercontent.com/johnisanerd/ApifyPublicData/main/assets/guides/install_mcp_into_claude_ai.png)

On claude.ai you add Apify as a connector, then enable just this Actor's tool.

1. Go to **Settings → Connectors → Browse connectors** and search for **Apify MCP server**. Install it (enable or update if prompted).
2. When connecting, authenticate with your Apify API token, and enable the tool `johnvc/agoda-hotel-api`.
3. In any chat, open **+ → Connectors** and turn on **Apify**.
4. Alternatively, choose **Add custom connector** and paste the full MCP URL `https://mcp.apify.com/?tools=actors,docs,johnvc/agoda-hotel-api`, using OAuth when prompted.
5. Ask Claude to run the Agoda Hotel API.

Open Claude on the web: https://claude.ai

---

## Install in Cursor

![Install in Cursor](https://raw.githubusercontent.com/johnisanerd/ApifyPublicData/main/assets/guides/install_mcp_into_cursor.png)

Cursor reads MCP servers from a project file at `.cursor/mcp.json`.

1. In your project, create `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "apify": {
      "url": "https://mcp.apify.com/?tools=actors,docs,johnvc/agoda-hotel-api"
    }
  }
}
```

2. If you prefer token auth over browser OAuth, add a header:

```json
{
  "mcpServers": {
    "apify": {
      "url": "https://mcp.apify.com/?tools=actors,docs,johnvc/agoda-hotel-api",
      "headers": { "Authorization": "Bearer YOUR_APIFY_TOKEN" }
    }
  }
}
```

3. Open **Cursor → Settings → MCP** and confirm the **apify** server is connected (green dot).
4. In Composer or Chat, ask Cursor to call the Agoda Hotel API.

New to Cursor? Get it here: https://cursor.com/referral?code=XQP4VBLI3NNX

---

## Install in ChatGPT

![Install in ChatGPT](https://raw.githubusercontent.com/johnisanerd/ApifyPublicData/main/assets/guides/install_mcp_into_ChatGPT.png)

ChatGPT connects to the Apify MCP server through Developer mode (available on ChatGPT Pro, Plus, Business, Enterprise, and Education plans).

1. Click your profile icon, then go to **Settings > Apps**. If you do not see a **Create app** button, open **Advanced settings** and enable **Developer mode**.
2. Click **Create app** and fill out the form:
   - **Name:** Apify
   - **MCP Server URL:** `https://mcp.apify.com/?tools=actors,docs,johnvc/agoda-hotel-api`
   - **Authentication:** OAuth
3. Click **Create** and authorize the connection with Apify.
4. To use the app in a conversation, click **+** in the chat, choose **Developer mode**, and select **Apify**.

More help: https://docs.apify.com/platform/integrations/mcp

---

## Related APIs

- [Google Hotels API](https://apify.com/johnvc/google-hotels-search-scraper?fpr=9n7kx3) for aggregated hotel prices across sites
- [Google Flights API](https://apify.com/johnvc/Google-Flights-Data-Scraper-Flight-and-Price-Search?fpr=9n7kx3) for the flights half of a trip
- [Google Travel Explore API](https://apify.com/johnvc/google-travel-explore-api?fpr=9n7kx3) for destination discovery
- [Google Maps Places API](https://apify.com/johnvc/google-maps-places-api?fpr=9n7kx3) for what is around a property

---

## 🌐 About Alpha OSINT

This example repo is part of [Alpha OSINT](https://www.alphaosint.com), toolset of financial and operations data sources and APIs.
For support or requests for this actor, please start a ticket [directly on our support page](https://apify.com/johnvc/agoda-hotel-api/issues/open?fpr=9n7kx3).

---

[**Made with care**](https://apify.com/johnvc?fpr=9n7kx3)

*Use the Agoda Hotel API to power your rate monitoring, travel research, and hotel reviews workflows with reliable, structured results.*

Last Updated: 2026.08.23

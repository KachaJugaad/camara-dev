# CAMARA Canada Sandbox — Plain English Guide

> Every feature explained as if talking to a smart non-technical business owner.
> No jargon. No acronyms without expansion. No telco-speak.

---

## What does this sandbox do?

Canadian phone carriers (Rogers, Bell, Telus) have information about your
customers' phones that could prevent fraud — but there's no way for app
developers to access it yet. This sandbox lets developers test against
realistic simulations of that data before the carriers open their systems.

## What kind of information?

Three types:

### 1. SIM Swap Detection

**What it is:** When someone calls their carrier and gets a new SIM card
for an existing phone number — often because they've stolen that number.

**Why it matters:** If a fraudster swaps someone's SIM, they receive all
texts and calls to that number, including two-factor authentication codes.
Banks and apps can check: "Was this phone number's SIM card changed recently?"
If yes, block the transaction.

**Business value:** Stops account takeover fraud. Banks lose billions annually
to SIM swap attacks. One API call could prevent most of them.

### 2. Number Verification

**What it is:** Checking whether a phone number actually belongs to the
device making the request — without sending an SMS code.

**Why it matters:** Today, apps send you a text message code and ask you
to type it back. This is slow, costs money, and can be intercepted.
Number verification does the same check instantly through the carrier
network — no text message needed.

**Business value:** Faster signups, lower SMS costs, harder to spoof.

### 3. Location Verification

**What it is:** Checking whether a phone is actually in the geographic
area it claims to be in, using cell tower data instead of GPS.

**Why it matters:** GPS location on a phone can be faked with a $10 app.
Cell tower location cannot be easily faked. An e-commerce company can
check: "Is this buyer's phone actually in Toronto, or is the GPS lying?"

**Business value:** Reduces chargebacks from location-spoofed orders.

## What is the fraud score?

The sandbox combines all three signals into a single risk score (0-100):
- SIM swapped recently? +40 points
- Phone number doesn't match device? +30 points
- Device not where it claims? +30 points

A score of 0 means everything checks out. A score of 70+ means multiple
fraud signals fired — this is probably not a legitimate customer.

## Who should use this?

- **Banks and fintechs** building fraud detection
- **E-commerce companies** fighting chargebacks
- **Identity verification providers** adding telco signals
- **AI developers** integrating phone verification into agents
- **Carrier engineers** testing their CAMARA implementation

## How do I try it?

1. Install Docker on your computer
2. Run: `git clone https://github.com/KachaJugaad/camara-dev && cd camara-dev && docker compose up`
3. Open `http://localhost:3000` in your browser
4. Click "Use demo key" and try the playground

No carrier agreement. No approval process. No cost. Apache 2.0 open source.

## What is CAMARA?

CAMARA (pronounced "camera") is a global project backed by the GSMA
(the organization that represents mobile carriers worldwide) and the
Linux Foundation. It creates standard APIs so that every carrier in
every country exposes the same interface.

Think of it like USB — before USB, every device had its own connector.
CAMARA is the "USB" for telecom APIs. Instead of learning Rogers' proprietary
API, then Bell's different API, then Telus' different API, you learn CAMARA
once and it works with all of them.

## What does "Fall25 spec-compliant" mean?

CAMARA releases updated specifications twice a year. "Fall25" (also called
"Fall 2025") is the version this sandbox implements. When Canadian carriers
eventually open their APIs, they'll follow this same spec — so code tested
here will work there.

# Serving Katip: what a masking API costs to run

*24 Nov 2026. Measured on one Apple M3 Pro laptop (12 CPU cores: 6 performance, 6 efficiency; 18 GB),
onnxruntime 1.31.1 on CPU, Python 3.13. Raw results in [`results/`](results/), method in
[README.md](README.md).*

## In three lines

- On CPU, Katip's models cost between **$0.002 and $0.04 per 1,000 pages** to serve at a sub-second p95.
  Compute is not the cost. Idle capacity is, so a Katip API is priced as a floor plus usage.
- **int8 is free accuracy and 2.5× cheaper**: Base int8 gave the same output as fp32 on all 140 test
  documents at 2.5× the throughput, with a third of the memory.
- **Dynamic batching, the main lever on GPUs, didn't help here**: one window per call gave the best p95
  and the same throughput. And because the int8 models quantise per batch, batching can change a few masks.
  On CPU, throughput comes from cores and replicas.

## What was measured

One endpoint, `POST /v1/mask`, runs the product pipeline: Katip's rules, one name model and the leak check,
as `katip_mask.Masker("ai", model=…).mask()` does. Every 256-token window goes through a request queue
to a single model worker with a dynamic batcher (max batch, max wait). The load generator replays 200
one-page documents (500+ words, about 4,200 characters, about 1,000 model tokens each) built from Katip's
synthetic blind and held-out sets. Unless a row says otherwise the server ran 4 model threads, max batch
16, max wait 5 ms. A "page" is 500 words, as on the model cards.

Four variants: Nano int8 (2.6 MB), Mini int8 (31 MB), Base int8 (111 MB) and Base fp32 (440 MB, the only
fp32 file published), plus rules only.

**Correctness first.** With one window per call the server's output equals the SDK's on every document for
all three int8 models (160 documents and pages each). See *Batching changes answers* below for the batched case.

## Throughput, latency, memory

| | Rules only | Nano int8 | Mini int8 | Base int8 | Base fp32 |
| --- | --- | --- | --- | --- | --- |
| Pages/s, saturated (4 model threads) | 32.5 | 29.9 | 15.4 | 4.5 | 1.8 |
| Model tokens/s | – | 23,380 | 15,650 | 4,506 | 1,806 |
| CPU cores actually used | 1.0 | 1.6 | 4.2 | 4.1 | 4.0 |
| CPU-seconds per 1,000 pages (1 model thread, the most efficient) | 32 | 43 | 236 | 786 | 2,107 |
| One page alone: model + rules, ms (p50 at 25% load) | 0 + 40 | 35 + 38 | 124 + 35 | 295 + 35 | 615 + 34 |
| p95 at 25 / 50 / 75 / 90% of saturation, ms | 134 / 203 / 374 / 570 | 137 / 331 / 516 / 584 | 300 / 789 / 1,670 / 2,126 | 775 / 1,833 / 2,929 / 3,169 | 1,592 / 1,726 / 2,608 / 7,098 |
| Memory, loaded (RSS) / peak under load, MB | 68 / 70 | 89 / 185 | 143 / 377 | 235 / 548 | 685 / 708 |
| Cold start: new process to first answer, ms | 211 | 262 | 354 | 636 | 1,175 |
| of which ONNX session load, ms | – | 14 | 28 | 99 | 230 |
| Names hidden, 640 names in 140 synthetic documents | 624 | 635 | 635 | 638 | 638 |
| KVKK-Bench Overall (published, real-text name tracks) | – | 85.9 | 93.0 | 96.1 | not scored (same output as int8 here) |
| KVKK-Bench leaked, all tracks (published) | – | 7.0% | 4.3% | 3.1% | – |

p95 at 90% for Base fp32 is the tail of a server close to its limit.

What a product owner reads from this:

- **Nano is rules-bound, not model-bound.** It uses 1.6 cores at saturation and adding model threads
  doesn't help (29.6 pages/s on 1 thread, 29.6 on 6). The limit is the Python rules and the server's
  Global Interpreter Lock. The cheap fix is more processes, not a bigger box.
- **Mini and Base are model-bound and scale with cores**, but each extra thread does less: Mini goes
  4.9 → 9.2 → 15.4 → 17.1 pages/s on 1, 2, 4 and 6 threads, and its CPU cost per page rises from 236 to
  313 CPU-seconds per 1,000 pages. So: many single-thread replicas for cost, more threads per request only
  when latency needs it.
- **Accuracy per unit of cost.** Going Nano → Mini costs 5.5× the CPU per page for +7.1 KVKK-Bench points.
  Mini → Base costs 3.3× more for +3.1 points. On the synthetic legal documents all three hide 99%+ of
  names (the rules already hide 97.5%). The gap is on everyday prose, where Mini finds 72% of names and
  Base 84%.
- **int8 vs fp32 (Base).** Identical masked output on 140 of 140 documents, 2.5× the throughput (4.5
  vs 1.8 pages/s), a third of the memory (235 vs 685 MB loaded). The model cards' "quantising cost no
  accuracy" holds on this test too, and fp32 has no reason to be served.

## Latency targets set the real capacity

Saturation numbers flatter. For an interactive tool, say p95 under one second for a one-page document, the
same 4-thread box serves:

| Model | Load that keeps p95 under 1 s | Pages/s at that load | Pages per month, one box |
| --- | --- | --- | --- |
| Nano int8 | 90% (p95 584 ms) | 26.6 | 70 M |
| Mini int8, batching off | 60% (p95 580 ms) | 9.0 | 24 M |
| Base int8 | 25% (p95 775 ms) | 1.2 | 3.2 M |
| Base fp32 | none: a single page alone has p95 1.6 s | – | – |

Base int8 loses three quarters of its capacity to the latency target. So Base belongs in a **batch tier**
(a data room overnight, priced per page with no latency promise, at full 4.5 pages/s), and Mini is the
interactive default, as the web demo already decided for browser download size.

## Batching window vs p95

Open loop at 60% of capacity, varying the batcher:

| Max batch / max wait | Mini: mean batch | Mini: p50 / p95, ms | Mini: saturated pages/s | Base int8: p50 / p95, ms | Base int8: saturated pages/s |
| --- | --- | --- | --- | --- | --- |
| 1 / 0 ms (off) | 1.0 | **171 / 580** | 14.9 | **639 / 1,542** | **4.75** |
| 4 / 2 ms | 1.8 | 241 / 631 | 15.9 | 856 / 1,960 | 4.38 |
| 8 / 5 ms | 2.1 | 294 / 959 | 15.5 | 745 / 2,401 | 4.40 |
| 16 / 5 ms | 2.2 | 309 / 1,222 | 14.7 | 723 / 2,206 | 4.38 |
| 16 / 20 ms | 3.2 | 518 / 1,160 | 14.4 | 893 / 2,832 | 4.20 |
| 32 / 50 ms | 5.9 | 892 / 1,686 | 13.1 | 1,204 / 2,994 | 4.15 |

On a GPU, batching turns idle parallel hardware into throughput, so a longer window trades p95 for cost.
On these CPUs one 256-token window already keeps four cores busy. Bigger batches add 9–15% padding
(windows of unequal length) and waiting, and buy nothing: throughput is flat or lower, p95 is worse.
The product decision is to turn the batcher off for CPU serving and keep it for a GPU tier, where it would
have to be measured again.

## Batching changes answers

All three int8 files use dynamic quantisation: each matrix multiply picks its int8 scale from the whole
input tensor, so one document's numbers depend on the other documents in its batch. Measured on 160
documents and pages (2,600 masks each):

| | Nano int8 | Mini int8 | Base int8 | Base fp32 |
| --- | --- | --- | --- | --- |
| Documents that differ, batched vs one at a time | 0 | 5 | 0 | 1 |
| Masks gained or lost | 0 | 4 | 0 | 0 |
| Documents that differ between two batched runs | 1 | 6 | 1 | 1 |

Small, but for a privacy product "the same document can come back masked differently" is a support ticket
and an audit question. This is the same batch-invariance problem LLM providers face. Options, cheapest first:
serve without batching (it doesn't cost throughput here, see above); re-quantise statically with fixed
scales; or document it and make the leak check, not the model, the guarantee.

## Scale to zero

- **A new process answers its first page in 0.26 s (Nano) to 0.64 s (Base int8).** Loading the ONNX session
  is 14–99 ms of that. Scale to zero adds well under a second to the first request after a quiet spell.
- **Unloading the session inside a running process does not give the memory back** (Base int8 stays at
  235 MB, Mini at 143 MB, after the session is dropped). Scale to zero has to mean stopping the process or
  container, not dropping the model.
- **When it pays:** an always-on box costs the same at 0% and 90% load. At 10,000 pages a month on Mini
  (one small firm), an always-on AWS c7g.xlarge ($125/month) is $12.50 per 1,000 pages, over 2,000 times the
  marginal cost ($0.0053). Below a few million pages a month per box, scale to zero (or one shared box for all
  tenants) is the main cost lever. Above that, keep it warm.

## Cost per 1,000 pages

The hourly list price of a 4-vCPU machine divided by the pages it serves in an hour, using the Mac's measured
pages/s. **A cloud vCPU was not measured here.** If a vCPU is slower than an M3 Pro performance core, the cost
rises in the same proportion. The next roadmap step is to run this harness on one rented VM.

| Use | Pages/s (measured) | AWS c7g.xlarge, London, $0.1717/h | Hetzner CCX23, €0.1178/h | Hetzner CAX21, €0.0176/h |
| --- | --- | --- | --- | --- |
| Nano, p95 < 1 s | 26.6 | $0.0018 | €0.0012 | €0.0002 |
| Mini, p95 < 1 s, batching off | 9.0 | $0.0053 | €0.0037 | €0.0006 |
| Base int8, p95 < 1 s | 1.2 | $0.0394 | €0.0270 | €0.0040 |
| Base int8, batch job | 4.5 | $0.0106 | €0.0073 | €0.0011 |
| Base fp32, batch job | 1.8 | $0.0265 | €0.0182 | €0.0027 |

Per million model tokens (Mini, saturated, AWS): about $0.003. A small task-specific encoder on CPU is
priced per page, not per token, and its token cost is a rounding error.

The laptop: a £2,499 MacBook Pro written off over 36 months is £0.095 an hour if it did nothing else, so a
firm masking on its own laptops pays close to nothing extra for compute. That is the on-device tier.

## Price sheet for a Katip API (draft)

What managed PII APIs charge, list prices read 24 Nov 2026, converted to this experiment's page
(about 4,200 characters):

| Service | List price, first tier | Per 1,000 pages |
| --- | --- | --- |
| Amazon Comprehend, DetectPiiEntities | $0.0001 per 100 characters | about $4.20 |
| Azure AI Language, Standard text records¹ | $1.00 per 1,000 records of 1,000 characters | about $5.00 |
| Google Sensitive Data Protection, inspect + de-identify | $3 + $2 per GiB, first GiB a month free | about $0.02 |

¹ Read from Azure's Retail Prices API; the meter isn't labelled PII, so treat it as indicative.

So the market spans more than two orders of magnitude, and compute cost doesn't set the price. Katip's
price comes from what it does that these don't measure: Turkish legal text, a published benchmark,
reversible placeholders and a leak check that refuses to return text with a detected value still readable.
A first sheet, in dollars to match the cost table:

| Tier | Model | Promise | Price per 1,000 pages | Measured cost (AWS, above) | Margin on compute | Cost could rise this much before a loss |
| --- | --- | --- | --- | --- | --- | --- |
| On device | any, in the browser, Kalkan or the SDK | nothing leaves the machine | free (AGPL) or a firm licence | paid by the firm's own laptop | – | – |
| Fast | Nano | p95 < 1 s a page | $0.50 | $0.0018 | 99.6% | 280× |
| Standard | Mini | p95 < 1 s a page | $1.50 | $0.0053 | 99.6% | 280× |
| Accurate | Base int8 | p95 < 1 s a page | $4.00 | $0.039 | 99.0% | 100× |
| Accurate, batch | Base int8 | done within 24 hours | $2.00 | $0.011 | 99.5% | 190× |
| Floor | – | one tenant on a shared warm box | $29 a month, includes 10,000 Standard pages | a $125-a-month box shared by 5+ firms | – | – |

The floor covers the idle box: a $125-a-month AWS machine is paid for by five small firms. Below that,
scale to zero. The "could rise" column leaves room for a slower cloud vCPU, OCR and redundancy. Support,
storage and sales are not in it. Fast and Standard sit well under Comprehend and Azure. Accurate matches
Comprehend's list price, which is the claim KVKK-Bench has to back. Google's per-byte price is lower than
every tier except on-device, so Katip should not compete on price with general cloud DLP.
Prices are a draft for discussion, not published.

## Limits

- One machine, one run per setting, on a laptop that was also running other software. Expect a few percent
  of noise; the effects reported above (2.5×, 3–4× and similar) are far larger than that.
- Cloud costs assume a cloud vCPU does the work of one M3 Pro core. Not measured.
- Synthetic documents only. Real case files are longer and messier. Pages here are text; OCR (2–4.5 s a page
  in Katip's earlier VM measurements) would dominate the cost of scanned documents and is not included.
- A Python toy server. A production server would use several processes behind a load balancer, which is
  what the Nano result asks for.

## Sources for prices (read 24 Nov 2026)

- AWS EC2 on-demand, Linux, EU (London): AWS price data behind aws.amazon.com/ec2/pricing/on-demand,
  <https://b0.p.awsstatic.com/pricing/2.0/meteredUnitMaps/ec2/USD/current/ec2-ondemand-without-sec-sel/EU%20(London)/Linux/index.json>
  (c7g.xlarge $0.1717/h).
- Hetzner Cloud, prices excluding VAT: <https://www.hetzner.com/cloud/cost-optimized/> (CAX21 €0.0176/h),
  <https://www.hetzner.com/cloud/general-purpose/> (CCX23 €0.1178/h).
- Apple UK store, MacBook Pro 14-inch with M5 Pro from £2,499: <https://www.apple.com/uk/shop/buy-mac/macbook-pro/14-inch>.
- Amazon Comprehend: <https://aws.amazon.com/comprehend/pricing/> (DetectPiiEntities $0.0001 per 100-character
  unit, minimum 3 units a request).
- Google Sensitive Data Protection: <https://cloud.google.com/sensitive-data-protection/pricing> (inspection
  $3/GiB and transformation $2/GiB after the first free GiB a month).
- Azure AI Language: <https://azure.microsoft.com/en-us/pricing/details/cognitive-services/language-service/>,
  rate read from <https://prices.azure.com/api/retail/prices> (meter "Standard Text Records", $1 per 1,000).
- KVKK-Bench scores: model cards for [Nano](https://huggingface.co/f1k/katip-mask-nano),
  [Mini](https://huggingface.co/f1k/katip-mask-mini) and [Base](https://huggingface.co/f1k/katip-mask-base),
  and the [leaderboard](https://huggingface.co/spaces/f1k/kvkk-bench).

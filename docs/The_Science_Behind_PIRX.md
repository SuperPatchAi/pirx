# The Science Behind PiRX

### How a Running App Uses Math, Data, and Smart Computers to Help You Run Faster

---

## What Is PiRX?

Imagine you had a really smart friend who watched every single run you did. This friend knew your heart rate, your pace, how far you ran, and even how well you slept the night before. Now imagine that friend could look at all of that information and tell you: "Based on everything you've been doing, here's how fast you could race a 5K today."

That's PiRX.

PiRX stands for **Performance Intelligence Rx**. It's an app for runners that takes the data from your watch or fitness tracker and turns it into a single, easy-to-read number: your **Projected Time**. That number is how fast PiRX thinks you could race right now.

But PiRX doesn't just guess. It uses real science. Let's walk through how it works, step by step.

---

## Step 1: Collecting Your Running Data

Every time you go for a run with a GPS watch (like a Garmin or COROS), your watch records a lot of information:

- **How far** you ran (in kilometers or miles)
- **How fast** you ran (your pace)
- **Your heart rate** (how hard your heart was working)
- **How long** you ran
- **Elevation** (did you run up hills?)

PiRX connects to your watch and pulls all of this data in. It even looks back at the last 6 to 12 months of your running history. That way, it can see the big picture of your training, not just one run.

---

## Step 2: Cleaning the Data

Not all data is perfect. Sometimes your GPS signal goes wonky and says you ran a 2-minute mile (that would break a world record!). Sometimes a run gets labeled wrong, like a walk being saved as a run.

Before PiRX does any math, it cleans up your data. Here's what it throws out:

- Runs shorter than 3 minutes or less than 1 mile
- Runs where the pace is way too fast (faster than any human could actually run)
- Runs where the pace is way too slow (probably a walk, not a run)
- Activities that aren't actually runs (like bike rides accidentally saved as runs)

This cleaning step is really important. Research showed that cleaning data this way makes the app's predictions **12% more accurate**. That's a big deal.

---

## Step 3: Breaking Your Training Into Five Pieces

Now here's where it gets interesting. PiRX doesn't just look at "how much did you run?" It breaks your training into **five building blocks** called **Drivers**. Each driver measures a different part of what makes you fast:

### 1. Aerobic Base
This is your engine. It measures how much easy running you've been doing over the last few weeks. Easy running builds the foundation that everything else sits on top of. PiRX looks at your total running distance over the last 7, 21, and 42 days.

### 2. Threshold Density
This measures how much time you spend running at your "comfortably hard" pace, which scientists call your **lactate threshold**. This is the pace where your legs start to burn. Runners who spend more time near this pace tend to get faster.

### 3. Speed Exposure
This tracks your really fast running, like sprints and short intervals. Even distance runners need a little bit of speed work. PiRX checks how many minutes per week you spend running at high intensity.

### 4. Load Consistency
Being consistent matters. If you run 50 miles one week and then only 10 miles the next, that big swing makes it harder for your body to adapt. PiRX measures how steady and smooth your training has been from week to week.

### 5. Running Economy
Running economy is how efficient you are. Imagine two runners with the same heart rate. If one of them is running faster at that same heart rate, that runner has better economy. PiRX tracks whether your pace at the same heart rate is getting faster over time.

**The key rule**: These five drivers must always add up to your total improvement. If PiRX says you've improved by 15 seconds since your last race, the drivers show you exactly where those 15 seconds came from. Maybe 6 seconds came from more easy running, 5 seconds came from threshold work, and 4 seconds came from better consistency.

---

## Step 4: The Baseline Race

Every PiRX projection starts from a real number: an actual race you ran. This is called your **Baseline Race**.

Let's say you ran a 5K in 22 minutes and 30 seconds last October. That becomes your anchor point. PiRX then looks at everything you've done since then and calculates how much faster (or slower) your training supports compared to that race.

If you haven't raced recently, PiRX can estimate a baseline from your hardest training efforts. But it tells you it's less certain about that estimate by widening the range of its prediction.

---

## Step 5: The Projection Engine

This is the brain of PiRX. The **Projection Engine** takes your baseline race, adds up the adjustments from all five drivers, and produces your Projected Time.

Here's the simple version of the formula:

```
Projected Time = Baseline Time
                 - Aerobic Base improvement
                 - Threshold improvement
                 - Speed improvement
                 - Economy improvement
                 - Consistency improvement
```

For example:
- Baseline 5K: **22:30**
- Aerobic Base improved by **4 seconds**
- Threshold improved by **3 seconds**
- Speed improved by **2 seconds**
- Economy improved by **1 second**
- Consistency improved by **2 seconds**
- **Projected Time: 22:18**

PiRX also gives you a **Supported Range**, which is a window around the Projected Time. Instead of just saying "22:18," it might say "somewhere between 22:10 and 22:26." This range gets narrower when PiRX has more data and your training is consistent. It gets wider when things are uncertain.

---

## Step 6: Smart Weighting (Recent Training Matters More)

PiRX pays more attention to what you did recently than what you did two months ago. It uses a weighting system:

| Time Window | How Much It Counts |
|---|---|
| Last 7 days | 45% |
| Days 8 through 21 | 35% |
| Days 22 through 90 | 20% |

This makes sense. A great workout last Tuesday matters more than a great workout in January. But PiRX doesn't ignore the older stuff completely, because long-term fitness takes months to build.

---

## Step 7: Smoothing Out the Bumps

Here's a problem: what if you have one amazing run on a Monday but then a terrible run on Tuesday? Should your Projected Time bounce up and down every day?

No. PiRX uses something called **volatility dampening**. It blends each new projection with the previous one so the number doesn't jump around. The app only shows you a change when your projection moves by **2 seconds or more**. Anything smaller than that is just noise, not real improvement.

Think of it like a ship. PiRX doesn't change course for every little wave. It only turns when there's a real shift in direction.

---

## Step 8: Predicting Across Different Race Distances

Let's say your Baseline Race was a 5K. But you also want to know how fast you could run a 10K, or a 1500 meter race. How does PiRX figure that out?

It uses a formula called the **Power Law**, first discovered by a scientist named Peter Riegel in 1981:

```
Time at new distance = Time at known distance x (new distance / known distance) ^ exponent
```

The "exponent" is the magic number. It describes how well you hold your speed as the distance gets longer. A runner who is really good at long distances has a different exponent than a sprinter.

PiRX makes this personal. Instead of using the same exponent for everyone, it figures out **your** exponent based on your training patterns. If you do a lot of easy, long runs, your exponent suggests you'll scale better to longer races. If you do a lot of fast intervals, your exponent says you'll be relatively better at shorter races.

A massive study of over **164,000 runners** and **1.4 million race performances** showed that this personalized approach is **30% more accurate** than using a single fixed number for everyone.

---

## Step 9: Finding Runners Like You

When you first start using PiRX, it might not have a lot of data about you yet. So how does it make predictions early on?

It uses a technique called **K-Nearest Neighbors (KNN)**. In plain English, it finds three runners in its database who are most similar to you based on your race times, age, and body type. Then it looks at what happened to those runners when they trained a certain way, and uses that to estimate what will happen to you.

Research showed this method predicts marathon times within **4 minutes and 48 seconds** on average. That's only a **2.4% error**, which is really accurate.

As PiRX collects more of your data over time, it stops leaning on similar runners and builds a model that is completely personal to you.

---

## Step 10: Your Personal Brain (The LSTM Model)

After about 8 weeks of data, PiRX trains a small computer brain just for you. This is called an **LSTM** (Long Short-Term Memory) neural network. That sounds complicated, but here's what it means:

An LSTM is a type of artificial intelligence that is great at finding patterns in data that changes over time. It looks at the sequence of your training, not just individual workouts. It notices things like:

- "This runner always improves after 3 weeks of steady mileage."
- "This runner's pace drops when their sleep is bad for 5 days in a row."
- "This runner responds best to threshold workouts on Tuesdays."

Each runner gets their own personal model. Research found that **individual models outperform a single model shared by all runners**. Your body is unique, so your model should be too.

The LSTM is trained using a special process called **Optuna**, which tests 60 different setups to find the one that works best for your data.

---

## Step 11: Race Readiness

Knowing your Projected Time is great. But are you actually *ready* to race?

PiRX calculates an **Event Readiness** score from 0 to 100 that answers that question. It considers:

- **Structural alignment**: Does your training match what the race demands? (A 1500m race needs speed; a 10K needs endurance)
- **Specificity**: Have you been doing workouts that simulate race conditions?
- **Volatility**: Has your training been stable, or has it been all over the place?
- **Durability**: Can your body hold up under race-day stress?

| Score | What It Means |
|---|---|
| 95-100 | Race Ready |
| 88-94 | Sharpening (almost there) |
| 75-87 | Building (still developing) |
| 60-74 | Foundational (early stages) |

Readiness is separate from your Projected Time. You could have a great Projected Time but low Readiness because your training has been inconsistent. PiRX shows you both so you can make a smart decision about when to race.

---

## Step 12: Protecting Against Injury

PiRX also watches out for your safety. It tracks something called the **Acute-to-Chronic Workload Ratio (ACWR)**. This compares how much you ran in the last week to how much you've been running on average over the last month.

| ACWR Range | What It Means |
|---|---|
| 0.8 to 1.3 | Safe zone. You're training at a healthy level. |
| Above 1.5 | Danger zone. You've ramped up too fast. Injury risk goes up. |
| Below 0.6 | Detraining zone. You're not doing enough to maintain fitness. |

When PiRX sees your ACWR getting too high, it widens your Supported Range and lowers your Readiness score. It's telling you: "Slow down. Your body needs to catch up."

---

## Step 13: Learning About You Over Time

One of the coolest parts of PiRX is the module called **"What We're Learning About You."** Over months of use, PiRX discovers patterns in your training:

- "You respond best to polarized training" (lots of easy running plus some very hard running, with not much in between)
- "Your fastest improvements come after 3-week blocks of steady mileage"
- "Your running economy improves most in the spring"

This isn't coaching. PiRX never tells you what to do. It just shows you what the data says about how your body responds. You and your coach (if you have one) decide what to do with that information.

---

## Step 14: Talking to Your Data

PiRX includes an AI chat feature powered by the same type of technology behind ChatGPT. You can ask it questions in plain English:

- "Why did my projection improve this week?"
- "How has my threshold work changed over the last month?"
- "Am I ready for a 10K race?"

The chat searches through your personal data, finds the most relevant information, and gives you a clear answer using PiRX's own language (Projected Time, Supported Range, Drivers). It never makes up answers. Everything it says comes from your actual data.

---

## The Research Behind It All

PiRX isn't built on opinions. Every piece of the system is backed by published scientific studies:

| What PiRX Does | The Science Behind It |
|---|---|
| Cleans raw running data | Dash 2024 — data cleaning improved predictions by 12% |
| Scales times across distances | Riegel 1981 + Blythe & Kiraly 2016 (164,746 runners) |
| Finds similar runners early on | Lerebourg et al. 2023 — KNN with 2.4% error on marathon prediction |
| Trains personal AI models | Dash 2024 — individual LSTMs outperform global models |
| Measures training load response | Zrenner et al. 2021 (6,771 marathon finishers) |
| Detects training intensity patterns | Qin et al. 2025 (120 runners, polarized vs pyramidal) |
| Assesses fatigue and readiness | Chang et al. 2023 + Biro et al. 2024 (fatigue classification) |
| Predicts injury risk | Raju et al. 2026 — Random Forest with 98% accuracy |
| Handles GPS errors and outliers | Dash 2024 — Huber loss function (robust to bad data) |
| Validates accuracy | Lerebourg et al. 2023 — Bland-Altman analysis |

---

## How PiRX Is Different

Most running apps give you a number based on a formula that's the same for everyone. PiRX is different in three big ways:

**1. It's anchored to a real race.** Your projection starts from an actual performance, not a generic estimate.

**2. It's personal.** After enough data, PiRX builds a model that is 100% unique to you. No two runners get the same model.

**3. It shows its work.** Those five drivers break down exactly where your improvement comes from, measured in seconds. You never have to wonder "why did my number change?" PiRX tells you.

PiRX doesn't behave like a fitness tracker that gives you a daily score. It behaves more like a financial forecast for your running. It looks at the structural foundation of your training and tells you what that foundation can support right now.

---

## In Summary

Here's the full journey of your data through PiRX:

1. Your watch records your run
2. PiRX pulls the data from your watch
3. Bad or messy data gets cleaned up
4. Your training gets broken into five drivers
5. PiRX compares your current training to your baseline race
6. Recent training counts more than old training
7. Small daily changes get smoothed out
8. A personal AI model learns your unique patterns
9. Your Projected Time updates when real change happens (2+ seconds)
10. PiRX scales that projection across race distances
11. A Readiness score tells you if you're ready to race
12. Safety checks make sure you're not overtraining

All of this happens automatically, every time you sync a run. You just open the app and see your number.

That's the science behind PiRX.

---

*PiRX — Performance Intelligence Rx*
*Your training has a structure. Now you can see it.*

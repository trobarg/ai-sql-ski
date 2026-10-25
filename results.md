# Results (gpt-4o-mini)

Every question was run with all three prompting strategies. ✅/❌ means GPT's query returned the same rows as the hand-written answer key in `questions.txt`; ☐ means there's no key. Skim the ❌s yourself — some may be reasonable readings of a vague question.

| Strategy | Auto-checked correct |
|---|---|
| zero_shot | 7/10 |
| single_domain | 9/10 |
| cross_domain | 10/10 |

_Re-graded by hand after the run: single_domain on question 10 first auto-checked ✅ because the key only checked the name. Its SQL summed run lengths instead of lift vertical, so the total was wrong. The key now includes the total, and the score above reflects that._

## 1. Which lifts are closed right now?

Expected rows: `[('Ridge Tram',), ('Cougar Bowl',)]`

**zero_shot** — ✅

```sql
SELECT * FROM lift WHERE is_open = 0;
```

> Currently, the following lifts are closed: 

1. Ridge Tram (tram) - 60 seats, 2900 ft vertical
2. Cougar Bowl (chair) - 4 seats, 1800 ft vertical

Let me know if you need more information!

**single_domain** — ✅

```sql
SELECT name FROM lift WHERE is_open = 0;
```

> The lifts currently closed are the Ridge Tram and Cougar Bowl.

**cross_domain** — ✅

```sql
SELECT name FROM lift WHERE is_open = 0;
```

> The lifts that are closed right now are the Ridge Tram and Cougar Bowl.

## 2. How many guests are from Utah?

Expected rows: `[(13,)]`

**zero_shot** — ✅

```sql
SELECT COUNT(*) FROM guest WHERE home_state = 'UT';
```

> There are 13 guests from Utah.

**single_domain** — ✅

```sql
SELECT COUNT(*) FROM guest WHERE home_state = 'UT';
```

> There are 13 guests from Utah.

**cross_domain** — ✅

```sql
SELECT COUNT(*) AS guest_count FROM guest WHERE home_state = 'UT';
```

> There are 13 guests from Utah at the ski resort!

## 3. What is the longest groomed blue run, and which lift serves it?

Expected rows: `[('Gondola Glide', 'Eagle Gondola')]`

**zero_shot** — ✅

```sql
SELECT run.name, run.length_ft, lift.name FROM run JOIN lift ON run.lift_id = lift.lift_id WHERE run.difficulty = 'blue' AND run.is_groomed = 1 ORDER BY run.length_ft DESC LIMIT 1;
```

> The longest groomed blue run is "Gondola Glide," which measures 7,800 feet. It is served by the Eagle Gondola. Enjoy your skiing!

**single_domain** — ✅

```sql
SELECT r.name, r.length_ft, l.name AS lift_name 
FROM run r 
JOIN lift l ON r.lift_id = l.lift_id 
WHERE r.is_groomed = 1 AND r.difficulty = 'blue' 
ORDER BY r.length_ft DESC 
LIMIT 1;
```

> The longest groomed blue run is called "Gondola Glide," which is 7,800 feet long, and it is served by the "Eagle Gondola."

**cross_domain** — ✅

```sql
SELECT r.name, l.name, r.length_ft
FROM run r JOIN lift l ON r.lift_id = l.lift_id
WHERE r.difficulty = 'blue' AND r.is_groomed = 1
ORDER BY r.length_ft DESC LIMIT 1;
```

> The longest groomed blue run is called "Gondola Glide," and it is served by the "Eagle Gondola." It stretches 7,800 feet!

## 4. Which lift had the most scans in February 2026?

Expected rows: `[('Aspen Glade',)]`

**zero_shot** — ❌

```sql
SELECT lift_id, COUNT(scan_id) AS scan_count FROM lift_scan WHERE scan_time BETWEEN '2026-02-01' AND '2026-02-28' GROUP BY lift_id ORDER BY scan_count DESC LIMIT 1;
```

> The lift with the most scans in February 2026 was lift ID 2, with a total of 83 scans.

**single_domain** — ✅

```sql
SELECT l.name, COUNT(ls.scan_id) AS total_scans
FROM lift l JOIN lift_scan ls ON l.lift_id = ls.lift_id
WHERE strftime('%Y-%m', ls.scan_time) = '2026-02'
GROUP BY l.lift_id
ORDER BY total_scans DESC
LIMIT 1;
```

> The lift with the most scans in February 2026 was Aspen Glade, with a total of 84 scans.

**cross_domain** — ✅

```sql
SELECT l.name, COUNT(*) AS scan_count
FROM lift_scan ls JOIN lift l ON ls.lift_id = l.lift_id
WHERE strftime('%Y-%m', ls.scan_time) = '2026-02'
GROUP BY l.lift_id ORDER BY scan_count DESC LIMIT 1;
```

> The lift with the most scans in February 2026 was Aspen Glade, with a total of 84 scans.

## 5. Which guest rode lifts the most times, and how many rides was that?

Expected rows: `[('Sophia', 'Martinez', 31)]`

**zero_shot** — ❌

```sql
SELECT guest_id, COUNT(lift_id) AS ride_count FROM lift_scan GROUP BY guest_id ORDER BY ride_count DESC LIMIT 1;
```

SQL error: `no such column: guest_id`

> I'm sorry, but I couldn't find the answer to your question due to an error in the query. If you have any other questions, feel free to ask!

**single_domain** — ✅

```sql
SELECT g.first_name, g.last_name, COUNT(ls.scan_id) AS rides
FROM guest g JOIN pass p ON g.guest_id = p.guest_id 
JOIN lift_scan ls ON p.pass_id = ls.pass_id 
GROUP BY g.guest_id 
ORDER BY rides DESC 
LIMIT 1;
```

> The guest who rode the lifts the most times is Sophia Martinez, with a total of 31 rides!

**cross_domain** — ✅

```sql
SELECT g.first_name, g.last_name, COUNT(ls.scan_id) AS ride_count
FROM lift_scan ls JOIN pass p ON ls.pass_id = p.pass_id JOIN guest g ON p.guest_id = g.guest_id
GROUP BY g.guest_id ORDER BY ride_count DESC LIMIT 1;
```

> The guest who rode the lifts the most times is Sophia Martinez, with a total of 31 rides!

## 6. How much total revenue came from pass sales, broken down by pass type?

Expected rows: `[('Day Ticket', 2835.0), ('Season Adult', 4396.0), ('Season Youth', 2745.0), ('Season Senior', 1947.0), ('Night Ticket', 237.0)]`

**zero_shot** — ✅

```sql
SELECT pt.name, SUM(pt.price) AS total_revenue
FROM pass p
JOIN pass_type pt ON p.pass_type_id = pt.pass_type_id
GROUP BY pt.name;
```

> Here's the breakdown of total revenue from pass sales by type:

- Day Ticket: $2,835.00
- Night Ticket: $237.00
- Season Adult: $4,396.00
- Season Senior: $1,947.00
- Season Youth: $2,745.00

If you have any more questions, feel free to ask!

**single_domain** — ✅

```sql
SELECT pt.name, SUM(pt.price) AS total_revenue
FROM pass p
JOIN pass_type pt ON p.pass_type_id = pt.pass_type_id
GROUP BY pt.pass_type_id;
```

> Here’s the total revenue from pass sales, broken down by pass type:

- **Day Ticket**: $2,835.00
- **Season Adult**: $4,396.00
- **Season Youth**: $2,745.00
- **Season Senior**: $1,947.00
- **Night Ticket**: $237.00

If you have any more questions, feel free to ask!

**cross_domain** — ✅

```sql
SELECT pt.name, SUM(pt.price) AS total_revenue
FROM pass p JOIN pass_type pt ON p.pass_type_id = pt.pass_type_id
GROUP BY pt.pass_type_id;
```

> The total revenue from pass sales, broken down by pass type, is as follows:

- Day Ticket: $2,835.00
- Season Adult: $4,396.00
- Season Youth: $2,745.00
- Season Senior: $1,947.00
- Night Ticket: $237.00

If you need more information, feel free to ask!

## 7. Which instructor earned the most from lessons?

Expected rows: `[('Sierra', 'Vance')]`

**zero_shot** — ✅

```sql
SELECT instructor.first_name, instructor.last_name, SUM(lesson.hours * instructor.hourly_rate) AS total_earned
FROM instructor
JOIN lesson ON instructor.instructor_id = lesson.instructor_id
GROUP BY instructor.instructor_id
ORDER BY total_earned DESC
LIMIT 1;
```

> The instructor who earned the most from lessons is Sierra Vance, with a total of $2,590.00!

**single_domain** — ✅

```sql
SELECT i.first_name, i.last_name, SUM(l.hours * i.hourly_rate) AS total_earnings
FROM instructor i JOIN lesson l ON l.instructor_id = i.instructor_id
GROUP BY i.instructor_id ORDER BY total_earnings DESC LIMIT 1;
```

> The instructor who earned the most from lessons is Sierra Vance, with total earnings of $2,590.00.

**cross_domain** — ✅

```sql
SELECT i.first_name, i.last_name, SUM(i.hourly_rate * l.hours) AS earnings
FROM instructor i JOIN lesson l ON i.instructor_id = l.instructor_id
GROUP BY i.instructor_id ORDER BY earnings DESC LIMIT 1;
```

> The instructor who earned the most from lessons is Sierra Vance, with earnings of $2,590.00.

## 8. Do any expert skiers take lessons?

Expected rows: `[]`

**zero_shot** — ✅

```sql
SELECT DISTINCT g.guest_id FROM guest g JOIN lesson l ON g.guest_id = l.guest_id WHERE g.skill_level = 'expert';
```

> I couldn't find any information on expert skiers taking lessons at the moment.

**single_domain** — ✅

```sql
SELECT DISTINCT g.first_name, g.last_name 
FROM guest g JOIN lesson l ON g.guest_id = l.guest_id 
WHERE g.skill_level = 'expert';
```

> I couldn't find any expert skiers taking lessons at the ski resort.

**cross_domain** — ✅

```sql
SELECT DISTINCT g.guest_id
FROM guest g JOIN lesson l ON g.guest_id = l.guest_id
WHERE g.skill_level = 'expert';
```

> I couldn't find any expert skiers taking lessons.

## 9. What's the best lift for a beginner to ride?

_No answer key (subjective or open-ended) — judge by hand._

**zero_shot** — ☐ (check by hand)

```sql
SELECT lift.name FROM lift INNER JOIN run ON lift.lift_id = run.lift_id WHERE run.difficulty = 'green' AND lift.is_open = 1;
```

> The best lifts for beginners that are currently open are Bunny Hop, Pine Flat, and Aspen Glade. Enjoy your skiing!

**single_domain** — ☐ (check by hand)

```sql
SELECT l.name, r.name FROM lift l JOIN run r ON l.lift_id = r.lift_id WHERE r.difficulty = 'green' AND l.is_open = 1;
```

> The best lifts for a beginner to ride are:

- Bunny Hop (Easy Street)
- Pine Flat (Sunny Side)
- Pine Flat (Lazy Fox)
- Aspen Glade (Aspen Trail)

Enjoy your time on the slopes!

**cross_domain** — ☐ (check by hand)

```sql
SELECT l.name, COUNT(r.run_id) AS run_count
FROM lift l JOIN run r ON l.lift_id = r.lift_id
WHERE r.difficulty = 'green'
GROUP BY l.lift_id ORDER BY run_count DESC LIMIT 1;
```

> The best lift for a beginner to ride is the "Pine Flat," which has 2 green runs! Enjoy your skiing!

## 10. Who skied the most vertical feet?

Expected rows: `[('Sophia', 'Martinez', 47700)]`

**zero_shot** — ❌

```sql
SELECT g.first_name, g.last_name, SUM(l.vertical_ft) AS total_vertical
FROM guest g
JOIN lift_scan ls ON g.guest_id = ls.pass_id
JOIN lift l ON ls.lift_id = l.lift_id
GROUP BY g.guest_id
ORDER BY total_vertical DESC
LIMIT 1;
```

> The guest who skied the most vertical feet is Wyatt Hansen, with a total of 44,900 vertical feet!

**single_domain** — ❌ (right person, wrong total: summed run lengths, once per run on each lift)

```sql
SELECT g.first_name, g.last_name, SUM(r.length_ft) AS total_vertical
FROM guest g
JOIN lift_scan ls ON g.guest_id = (SELECT p.guest_id FROM pass p WHERE p.pass_id = ls.pass_id)
JOIN run r ON ls.lift_id = r.lift_id
GROUP BY g.guest_id
ORDER BY total_vertical DESC
LIMIT 1;
```

> The skier who logged the most vertical feet is Sophia Martinez, with a total of 402,300 feet!

**cross_domain** — ✅

```sql
SELECT g.first_name, g.last_name, SUM(l.vertical_ft) AS total_vertical
FROM lift_scan ls JOIN lift l ON l.lift_id = ls.lift_id 
JOIN pass p ON p.pass_id = ls.pass_id 
JOIN guest g ON g.guest_id = p.guest_id
GROUP BY g.guest_id ORDER BY total_vertical DESC LIMIT 1;
```

> The skier who logged the most vertical feet is Sophia Martinez, with a total of 47,700 vertical feet!

## 11. How busy is the mountain on weekends compared to weekdays?

_No answer key (subjective or open-ended) — judge by hand._

**zero_shot** — ☐ (check by hand)

```sql
SELECT strftime('%w', scan_time) AS day_of_week, COUNT(*) AS total_scans
FROM lift_scan
GROUP BY day_of_week
HAVING day_of_week IN ('0', '6');
```

> The mountain tends to be busier on weekends compared to weekdays. On Sundays, there were 37 scans, while Saturdays had 31 scans.

**single_domain** — ☐ (check by hand)

```sql
SELECT strftime('%w', scan_time) AS day_of_week, COUNT(scan_id) AS total_scans
FROM lift_scan
GROUP BY day_of_week;
```

> It looks like I couldn't find specific comparisons for how busy the mountain is on weekends versus weekdays. However, the scans indicate more activity on Fridays (71 scans) and a decent amount on Saturdays (37 scans), while weekdays generally show varying levels of busyness. If you have more detailed questions, feel free to ask!

**cross_domain** — ☐ (check by hand)

```sql
SELECT strftime('%w', scan_time) AS day_of_week, COUNT(*) AS lift_scans
FROM lift_scan
GROUP BY day_of_week
HAVING day_of_week IN ('0', '6');
```

> It looks like the mountain is busier on weekends compared to weekdays, with 37 lift scans on Sunday and 31 on Saturday. If you enjoy less crowded slopes, weekdays might be the way to go!

## 12. Which runs can I ski today if I only ride open lifts and want black diamonds?

Expected rows: `[('High Noon',), ('Eagles Nest',), ('Powder Keg',)]`

**zero_shot** — ✅

```sql
SELECT run.name FROM run JOIN lift ON run.lift_id = lift.lift_id WHERE lift.is_open = 1 AND run.difficulty = 'black';
```

> Today, you can ski the following black diamond runs: High Noon, Eagles Nest, and Powder Keg. Enjoy!

**single_domain** — ✅

```sql
SELECT r.name FROM run r JOIN lift l ON r.lift_id = l.lift_id WHERE l.is_open = 1 AND r.difficulty = 'black';
```

> You can ski the following black diamond runs today if you use open lifts: High Noon, Eagles Nest, and Powder Keg. Enjoy your time on the slopes!

**cross_domain** — ✅

```sql
SELECT r.name
FROM run r JOIN lift l ON r.lift_id = l.lift_id
WHERE l.is_open = 1 AND r.difficulty = 'black';
```

> You can ski the following black diamond runs today: High Noon, Eagles Nest, and Powder Keg. Enjoy your day on the slopes!


---
Total usage: 30279 input + 2626 output tokens on gpt-4o-mini ≈ $0.0061

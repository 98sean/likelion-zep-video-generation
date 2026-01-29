# Optimization Roadmap: 900 Quizzes/Day

## Quick Reference: Where to Fix

### 🔴 CRITICAL (4x improvement)
**File**: `src/quiz_batch.py`
**Lines**: 59-75
**Issue**: Sequential topic processing blocks parallelization

```python
# ❌ CURRENT (Sequential)
for i, topic in enumerate(trends, start=1):
    print(f"\n=== Trend #{i}: {topic} ===")
    try:
        raw_quiz = create_quizzes(topic)  # WAITS here for 30-60s
        # ... process quiz
```

**Fix**: Use `ThreadPoolExecutor` for concurrent processing
```python
# ✅ FIXED (Parallel)
from concurrent.futures import ThreadPoolExecutor, as_completed

with ThreadPoolExecutor(max_workers=4) as executor:
    futures = {executor.submit(create_quizzes, topic): topic for topic in trends}
    for future in as_completed(futures):
        topic = futures[future]
        raw_quiz = future.result()
        # ... process quiz
```

**Impact**: 4x faster (450s → 112s for 15 topics)

---

### 🟠 HIGH (1.5x improvement)
**File**: `src/generate_quiz.py`
**Lines**: 300-363
**Issue**: Each topic requires 2 sequential API calls (generate + validate)

```python
# ❌ CURRENT (2 API calls per topic)
def create_quizzes(topic: str, max_trial=3):
    # Call 1: Generate quiz (30-40s)
    response = client.chat.completions.create(
        model="gpt-5-mini",
        messages=[{"role": "user", "content": current_prompt}],
    )

    # Call 2: Validate quiz (25-35s)
    new_valid_questions, reason = validate_with_ai(cleaned_data, topic)
```

**Option A - Skip Validation (Fastest)**:
```python
# ✅ FIXED (Skip validation for speed)
def create_quizzes(topic: str, max_trial=3, validate_ai=True):
    # ... generate quiz ...

    if validate_ai:
        new_valid_questions, reason = validate_with_ai(cleaned_data, topic)
    else:
        new_valid_questions = cleaned_data.get("questions", [])
    # ...

# In quiz_batch.py:
raw_quiz = create_quizzes(topic, validate_ai=False)  # 30-40s instead of 60-75s
```

**Option B - Batch Validation (Balanced)**:
```python
# ✅ FIXED (Validate 3 topics together)
def create_quizzes_batch(topics: list):
    quizzes = []
    for topic in topics:
        quiz = create_quizzes(topic, validate_ai=False)  # Generate without validation
        quizzes.append((topic, quiz))

    # Validate all at once (cheaper batch call)
    validate_with_ai_batch(quizzes)
    return quizzes
```

**Impact**: 1.5x faster (60-75s → 40-50s per topic)

---

### 🟡 MEDIUM (Small improvements)

#### Issue 1: TARGET_COUNT = 10 (Line 301)
```python
# ❌ CURRENT
TARGET_COUNT = 10  # Ambitious target, causes retries

# ✅ OPTION
TARGET_COUNT = 8  # Easier to achieve, fewer rejections
```

**Impact**: 15-20% faster generation

---

#### Issue 2: Too Long Batch Interval (Line 16, auto_quiz_scheduler.py)
```python
# ❌ CURRENT
LOOP_INTERVAL = 420  # 7 minutes

# ✅ FIXED
LOOP_INTERVAL = 120  # 2 minutes (after Phase 1 optimization)
```

**Impact**: More batches per day (if processing time < 2 min)

---

## Step-by-Step Implementation

### Step 1: Parallelize Topic Processing (Do First)
1. Edit `src/quiz_batch.py`
2. Replace lines 59-75 with ThreadPoolExecutor loop
3. Keep same data structure for downstream code
4. Test with 4 parallel workers
5. Expected result: 4x faster (600 quizzes/day)

### Step 2: Optimize Validation (Do Second)
1. Edit `src/generate_quiz.py` line 300
2. Add `validate_ai=True` parameter to `create_quizzes()`
3. Edit `src/quiz_batch.py` to pass `validate_ai=False`
4. Test quality of generated quizzes
5. Expected result: 900 quizzes/day

### Step 3: Fine-tune Settings
1. Adjust `TARGET_COUNT` if needed (currently 10)
2. Reduce `LOOP_INTERVAL` to 2 minutes
3. Monitor for API rate limits
4. Track total quiz count daily

---

## Testing Checklist

After each phase, verify:

- [ ] Quizzes are still valid JSON format
- [ ] Questions have all required fields (question, options, answer)
- [ ] Answer exists in options list
- [ ] No duplicate questions
- [ ] API error handling works
- [ ] Daily count increases as expected

---

## Expected Timeline

| Phase | Effort | Result |
|-------|--------|--------|
| Phase 1 (Parallel) | 2-4 hours | 600 quizzes/day |
| Phase 2 (Validation) | 2-3 hours | 900 quizzes/day |
| Phase 3 (Tuning) | <1 hour | Stabilize at 900 |

---

## Monitoring Queries

Add these to track progress:

```python
# Track quiz generation rate
import os
quiz_files = os.listdir("data")
total_quizzes = sum(len(json.load(open(f"data/{f}"))) for f in quiz_files if f.endswith(".json"))
print(f"Total quizzes generated: {total_quizzes}")

# Track time per batch
batch_times = []  # Append time.time() - batch_start after each cycle
avg_time = sum(batch_times) / len(batch_times)
quizzes_per_second = 150 / avg_time if avg_time > 0 else 0
daily_rate = quizzes_per_second * 86400
print(f"Average batch: {avg_time:.1f}s")
print(f"Daily rate: {daily_rate:.0f} quizzes/day")
```

---

## Configuration Changes Needed

Add to `src/config.py`:

```python
# Performance tuning
PARALLEL_WORKERS = 4          # Number of concurrent topic threads
VALIDATE_AI = False            # Skip AI validation for speed
TARGET_QUIZZES_PER_TOPIC = 8  # Questions per topic
BATCH_INTERVAL = 120          # Seconds between batches (2 minutes)
```

Then use in other files:
```python
from .config import PARALLEL_WORKERS, VALIDATE_AI, BATCH_INTERVAL

# In quiz_batch.py
with ThreadPoolExecutor(max_workers=PARALLEL_WORKERS) as executor:
    # ...

# In generate_quiz.py
def create_quizzes(topic: str, validate_ai=VALIDATE_AI):
    # ...
```


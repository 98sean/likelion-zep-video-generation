# Performance Analysis: 900 Quizzes Per Day Goal

## Executive Summary

Current system generates ~150 quizzes per day. To reach **900 quizzes/day** requires **6x throughput improvement**.

### Current Daily Output
- **Topics per batch**: 15 (from `quiz_batch.py:51`)
- **Questions per topic**: 10 (from `generate_quiz.py:301`)
- **Batch frequency**: Every 7 minutes (420 seconds) via `auto_quiz_scheduler.py`
- **Theoretical max**: ~206 quizzes/day (15 topics × 10 questions, running 24/7 every 7 min)
- **Actual**: ~150/day (accounting for API latency, validation failures, retries)

**Target**: 900 quizzes/day = 6x improvement

---

## Critical Bottlenecks

### 1. **Sequential Topic Processing** (HIGHEST IMPACT)
**Location**: `src/quiz_batch.py:59-75` and `src/auto_quiz_scheduler.py:34-63`

```python
for i, topic in enumerate(trends, start=1):
    raw_quiz = create_quizzes(topic)  # WAITS for completion before next topic
```

**Problem**: Topics are processed one-by-one. Each `create_quizzes()` call blocks until complete.

**Impact**: If each topic takes 30-60 seconds (3 API calls × 10-20s each), 15 topics take 450-900 seconds per batch.

**Solution**: Process topics in **parallel** using `asyncio` or `concurrent.futures.ThreadPoolExecutor`
- Current: 15 topics × 60s = 15 minutes sequential
- With parallel (4 workers): 15 topics ÷ 4 × 60s = 4 minutes (~4x faster)

---

### 2. **Double AI Validation (MEDIUM-HIGH IMPACT)**
**Location**: `src/generate_quiz.py:300-363`

```python
# API Call #1: Generate quiz
response = client.chat.completions.create(model="gpt-5-mini", ...)

# API Call #2: Validate/fact-check
new_valid_questions, reason = validate_with_ai(cleaned_data, topic)
```

**Problem**: Every quiz generation requires 2 sequential API calls:
1. GPT-5-mini: Generate questions (~15-25s)
2. GPT-5.1: Validate answers (~15-25s)

**Impact**: 2 API calls × 15-25s = 30-50s per topic, done sequentially

**Options**:
- **Quick win**: Use cheaper/faster model for validation (gpt-4-turbo instead of gpt-5.1)
- **Better**: Batch validation - generate 3 topics, then validate all together
- **Best**: Remove strict validation, accept partial results (trade quality for speed)

---

### 3. **Validation Strictness** (MEDIUM IMPACT)
**Location**: `src/generate_quiz.py:152-234` (validate_with_ai)

**Problem**:
- Only 1 generation attempt per topic (max_trial=3 in line 305, but effectively 1-2)
- AI fact-checker rejects batches that don't meet strict criteria
- Retry loop adds 1-3 seconds between attempts

**Current success rate**: ~60-70% of first attempts pass validation
- 15 topics × 70% success = ~10.5 valid topics per batch
- Remaining 4.5 topics retry (adds 30-60 seconds)

**Solutions**:
- Lower validation threshold (accept 8 questions instead of 10)
- Accept partial batches without retry
- Skip AI fact-check for faster generation mode

---

### 4. **Batch Interval Too Long** (LOW-MEDIUM IMPACT)
**Location**: `src/auto_quiz_scheduler.py:16`

```python
LOOP_INTERVAL = 420  # 7 minutes
```

**Current**: Batch runs every 7 minutes
- 24 hours ÷ 7 min = 205 batches
- 205 batches × 150 quizzes = ~31,000 quizzes (theoretical if no failures)

**Problem**: Too much time between batches, batch still takes 3-5 minutes to process

**Solution**: Reduce to 2-3 minutes interval, or make processing truly async

---

### 5. **Sequential Video Generation** (NOT BLOCKING QUIZ GEN)
**Location**: `src/auto_quiz_scheduler.py:159-182`

```python
for idx, quiz in enumerate(quizzes, start=1):
    make_video(quiz, output_path=output_path)  # Sequential
```

**Note**: This is AFTER quiz generation, doesn't block quiz throughput. But can be parallelized separately if needed.

---

## Recommendations (Priority Order)

### Phase 1: Parallel Topic Processing (4x improvement → 600 quizzes/day)
**Time to implement**: 2-4 hours
**Code changes**: `src/quiz_batch.py` + `src/auto_quiz_scheduler.py`

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def run_quiz_batch():
    topics = fetch_trending_topics(n=15)

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(create_quizzes, topic): topic for topic in topics}

        for future in as_completed(futures):
            quiz = future.result()
            all_quizzes.extend(flatten_questions(topics[future], quiz))
```

---

### Phase 2: Optimize Validation (1.5x improvement → 900 quizzes/day)
**Time to implement**: 2-3 hours
**Options**:

**Option A** (Fastest): Skip AI validation for speed mode
```python
def create_quizzes(topic: str, validate_ai=False):
    # Skip lines 345-351 if validate_ai=False
```
- Saves 25-40 seconds per topic
- Trade-off: Quality (may have factual errors)

**Option B** (Balanced): Lower TARGET_COUNT to 8-9 questions
```python
TARGET_COUNT = 8  # Instead of 10
```
- Reduces generation time by 20-30%
- Fewer AI validation rejections
- Impacts quiz variety

**Option C** (Best): Batch validation
```python
# Generate 3 topics' quizzes, validate all together
quizzes_batch = [create_quizzes(topic, validate=False) for topic in topics[:3]]
validate_with_ai_batch(quizzes_batch)
```

---

### Phase 3: Increase Batch Frequency
**Time to implement**: < 1 hour
**Change**: `src/auto_quiz_scheduler.py:16`

```python
LOOP_INTERVAL = 120  # 2 minutes instead of 7
```

**Assumption**: Phase 1 + 2 reduces batch time from 5-10 min to 1-2 min
- 1440 min/day ÷ 2 min per batch = 720 batches
- 720 batches × 1.25 quizzes = 900 quizzes/day

---

## Performance Metrics to Track

Add monitoring to measure improvement:

```python
import time

def create_quizzes_monitored(topic: str):
    start = time.time()

    # Generate
    gen_start = time.time()
    raw_quiz = ...
    gen_time = time.time() - gen_start

    # Validate
    val_start = time.time()
    validate_with_ai(...)
    val_time = time.time() - val_start

    total = time.time() - start
    print(f"{topic}: gen={gen_time:.1f}s, val={val_time:.1f}s, total={total:.1f}s")

    return total
```

---

## Implementation Plan

| Phase | Changes | Effort | Expected Result | Total Quizzes/Day |
|-------|---------|--------|-----------------|-------------------|
| Current | None | - | Sequential processing | 150 |
| Phase 1 | Parallel topics (4 workers) | 2-4h | 4x faster topic processing | 600 |
| Phase 2 | Skip/batch AI validation | 2-3h | 1.5x faster validation | 900 |
| Phase 3 | Reduce batch interval | <1h | Continuous processing | 900+ |

---

## Files Requiring Changes

1. **`src/quiz_batch.py`** (Lines 59-75)
   - Replace sequential loop with ThreadPoolExecutor
   - Use concurrent topic processing

2. **`src/generate_quiz.py`** (Lines 300-363)
   - Add parameter to skip/batch AI validation
   - Lower TARGET_COUNT or accept partial results

3. **`src/auto_quiz_scheduler.py`** (Line 16)
   - Reduce LOOP_INTERVAL to 2-3 minutes
   - Optionally parallelize video generation

4. **`src/config.py`** (New)
   - Add configuration flags for validation mode
   - Add worker pool size setting

---

## Risk Assessment

| Change | Risk | Mitigation |
|--------|------|-----------|
| Parallel topics | Race conditions in file I/O | Use locks on JSON file writes |
| Skip validation | Quality degradation | Run quality audit before production |
| Faster models | Higher costs | Monitor OpenAI spend |
| More batches | API rate limits | Add exponential backoff retry |


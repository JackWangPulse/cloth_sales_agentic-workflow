# Apparel Seed Data Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a separate apparel seed SQL file with 100 products while preserving the existing footwear seed file.

**Architecture:** Reuse the existing `products` insert shape and preserve stable identifiers (`brand_code`, `sku`, timestamps). Only replace apparel-specific business content (`name`, `tags`, `attributes`) so downstream code can switch datasets with minimal schema impact.

**Tech Stack:** SQL seed data, PowerShell generation, existing MySQL schema

---

### Task 1: Create apparel seed file

**Files:**
- Create: `sql/seed_data_apparel.sql`
- Modify: `docs/superpowers/plans/2026-03-28-seed-data-apparel.md`

- [ ] **Step 1: Inspect existing product seed layout**

Confirm the `products` insert columns and the first 100 records in `sql/seed_data.sql` so the new file matches the current schema and identifier set.

- [ ] **Step 2: Generate apparel variants for the 100 products**

Map the existing 100 product rows to apparel-oriented values:
- keep `brand_code`
- keep `sku`
- keep `created_at`
- keep `updated_at`
- replace `name`
- replace `tags`
- replace `attributes`

- [ ] **Step 3: Write `sql/seed_data_apparel.sql`**

Create a standalone seed file that only inserts apparel-style `products` data and leaves the existing `sql/seed_data.sql` untouched.

- [ ] **Step 4: Verify file shape**

Check:
- file is UTF-8 readable
- insert columns match current schema
- record count is 100

- [ ] **Step 5: Report import usage**

Document the import command in the final response so the user can choose the apparel seed file explicitly.

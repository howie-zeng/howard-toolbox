#!/usr/bin/env Rscript
# export_macro_lookups.R
# -------------------------------------------------------------------
# Exports FICO_BKT_COUPON.csv from R static pool data for the Python
# simulation engine.
#
# Self-contained: only needs data.table (no arrow dependency).
# Sources config.R for paths/constants, inlines the few functions
# needed from processing.R.
#
# Outputs:
#   input/macro/FICO_BKT_COUPON.csv
#
# Usage:
#   Rscript tools/export_macro_lookups.R [output_dir]
#   (default output_dir = "input/macro")
# -------------------------------------------------------------------

library(data.table)

# ── Source config only (paths, constants, no heavy deps) ─────────
UTILS_DIR <- "S:/QR/jli/GitHub/RCode/MPL/utils_NEW"
source(file.path(UTILS_DIR, "config.R"))

# ── Inlined helpers from processing.R (avoid arrow dependency) ───

fast_bucket <- function(x, breaks, labels, right_closed = FALSE) {
  idx <- findInterval(x, breaks,
                      rightmost.closed = TRUE,
                      left.open = right_closed)
  out <- labels[idx]
  out[idx < 1L | idx > length(labels)] <- NA_character_
  out[is.na(x)] <- NA_character_
  return(out)
}

add_months_ym <- function(ym_str, n) {
  y <- as.integer(substr(ym_str, 1, 4))
  m <- as.integer(substr(ym_str, 6, 7))
  idx <- (m - 1L) + n
  y2 <- y + idx %/% 12L
  m2 <- (idx %% 12L) + 1L
  sprintf("%04d-%02d", y2, m2)
}

load_static_pool <- function(platform, deal_name) {
  folder <- PLATFORM_FOLDERS[[platform]]
  if (is.null(folder)) stop("No folder mapping for platform: ", platform)
  clean_name <- gsub("[^A-Za-z0-9_]", "_", deal_name)
  path <- file.path(R_DATADIR, folder, paste0(clean_name, "_static.rds"))
  if (!file.exists(path)) stop("Static pool file not found: ", path)
  cat(sprintf("  Loading: %s\n", basename(path)))
  dt <- as.data.table(readRDS(path))
  if (inherits(dt$vintage_month_dv01, "Date")) {
    set(dt, j = "vint_moyy", value = format(dt$vintage_month_dv01, "%Y-%m"))
  } else {
    set(dt, j = "vint_moyy", value = substr(as.character(dt$vintage_month_dv01), 1, 7))
  }
  cat(sprintf("    Rows: %d  Vintages: %d\n", nrow(dt), uniqueN(dt$vint_moyy)))
  return(dt)
}

load_all_static_pools <- function() {
  cat("Loading all static pool data...\n")
  all_plat_names <- names(DEAL_NAMES)
  all_deal_names <- unlist(DEAL_NAMES, use.names = FALSE)
  by_platform <- vector("list", length(all_plat_names))
  names(by_platform) <- all_plat_names
  for (i in seq_along(all_plat_names)) {
    by_platform[[all_plat_names[i]]] <- load_static_pool(
      all_plat_names[i], all_deal_names[i]
    )
  }
  combined <- rbindlist(by_platform, use.names = TRUE, fill = TRUE,
                        idcol = "source_platform")
  cat(sprintf("  Total: %d rows across %d platforms\n",
              nrow(combined), length(by_platform)))
  return(list(by_platform = by_platform, combined = combined))
}

compute_fico_coupon <- function(static_dt,
                                forward_months = FICO_COUPON_FORWARD_MONTHS) {
  work <- static_dt[loan_balance_orig > 0,
                    .(loan_rate_gross_orig, loan_balance_orig, vint_moyy,
                      fico_bkt = fast_bucket(fico_orig,
                                             FICO_BUCKET_BREAKS,
                                             FICO_BUCKET_LABELS))]
  work <- work[!is.na(fico_bkt)]
  base <- work[, .(
    fico_bkt_coupon = weighted.mean(loan_rate_gross_orig,
                                    loan_balance_orig,
                                    na.rm = TRUE)
  ), by = .(vint_moyy, fico_bkt)]

  if (forward_months > 0) {
    fwd_list <- vector("list", forward_months + 1L)
    fwd_list[[1L]] <- base
    for (n in seq_len(forward_months)) {
      tmp <- copy(base)
      set(tmp, j = "vint_moyy", value = add_months_ym(tmp$vint_moyy, n))
      fwd_list[[n + 1L]] <- tmp
    }
    out <- rbindlist(fwd_list, use.names = TRUE)
  } else {
    out <- base
  }

  out <- unique(out, by = c("fico_bkt", "vint_moyy"), fromLast = FALSE)
  setkey(out, vint_moyy, fico_bkt)
  return(out)
}

# ── Parse args ──────────────────────────────────────────────────────
args <- commandArgs(trailingOnly = TRUE)
output_dir <- if (length(args) >= 1) args[1] else "input/macro"
dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

cat("=== Exporting FICO_BKT_COUPON.csv ===\n\n")

# ── 1. Load all static pools ────────────────────────────────────────
pools <- load_all_static_pools()
all_static <- pools$combined

# ── 2. Compute cross-platform FICO coupon lookup ────────────────────
cat("\nComputing cross-platform FICO coupon lookup...\n")
fico_all <- compute_fico_coupon(all_static)

cat(sprintf("  Rows: %d\n", nrow(fico_all)))
cat(sprintf("  Vintage range: %s to %s\n",
            min(fico_all$vint_moyy), max(fico_all$vint_moyy)))
cat(sprintf("  FICO buckets: %s\n",
            paste(unique(fico_all$fico_bkt), collapse = ", ")))

# Convert vint_moyy from YYYY-MM to YYYYMM for Python loader
fico_all[, vint_moyy := gsub("-", "", vint_moyy)]

fico_out <- file.path(output_dir, "FICO_BKT_COUPON.csv")
fwrite(fico_all, fico_out)
cat(sprintf("\n  Wrote: %s (%d rows)\n", fico_out, nrow(fico_all)))
cat("=== Done ===\n")

#!/usr/bin/env Rscript
# dump_gam_to_coef.R  (v2)
# -------------------------------------------------------------------
# Dumps mgcv GAM models to TSV coef files for model_coef.read().
#
# Strategy: predict(gam, newdata, type="terms") gives each term's partial
# contribution, handling identifiability constraints, penalized splines, and
# by-variables automatically.
# -------------------------------------------------------------------

library(mgcv)

# ============== Helpers ==============

unwrap_formula <- function(name) {
  # Recursively strip R formula wrappers, keeping only the first argument.
  # ordered(v_opti) -> v_opti, ns(age, 3) -> age, pmax(x, 2021) -> x
  while (grepl("^[a-zA-Z_.][a-zA-Z0-9_.]*\\(", name)) {
    inner <- sub("^[a-zA-Z_.][a-zA-Z0-9_.]*\\((.*)\\)$", "\\1", name)
    if (inner == name) break  # no match
    # Keep only first argument (split at depth-0 comma)
    depth <- 0
    for (i in seq_len(nchar(inner))) {
      ch <- substr(inner, i, i)
      if (ch == "(") depth <- depth + 1
      else if (ch == ")") depth <- depth - 1
      else if (ch == "," && depth == 0) {
        inner <- substr(inner, 1, i - 1)
        break
      }
    }
    name <- trimws(inner)
  }
  name
}

# Backwards-compat alias
extract_clean_var <- unwrap_formula

extract_bounds_from_term <- function(term_label) {
  lo <- NA_real_; hi <- NA_real_
  if (grepl("pmin\\(", term_label)) {
    m <- regmatches(term_label, regexpr("[0-9.e+-]+\\)$", term_label))
    if (length(m) == 1) hi <- as.numeric(sub("\\)$", "", m))
  }
  if (grepl("pmax\\(", term_label)) {
    m <- regmatches(term_label, regexpr("pmax\\([^,]+,\\s*([0-9.e+-]+)\\)", term_label))
    if (length(m) == 1) lo <- as.numeric(sub(".*,\\s*([0-9.e+-]+)\\).*", "\\1", m))
  }
  list(lo = lo, hi = hi)
}

is_ordered_by <- function(smooth_obj) {
  # ordered(v_opti) with by.level=1 is a v-flag indicator, treat as numeric
  by <- smooth_obj$by
  !is.null(by) && !is.na(by) && grepl("^ordered\\(", by)
}

is_factor_by <- function(smooth_obj) {
  by <- smooth_obj$by
  if (is.null(by) || is.na(by) || by == "NA") return(FALSE)
  if (is_ordered_by(smooth_obj)) return(FALSE)
  bl <- smooth_obj$by.level
  !is.null(bl) && length(bl) > 0 && nchar(trimws(bl)) > 0
}

is_numeric_by <- function(smooth_obj) {
  by <- smooth_obj$by
  if (is.null(by) || is.na(by) || by == "NA") return(FALSE)
  if (is_ordered_by(smooth_obj)) return(TRUE)
  !is_factor_by(smooth_obj)
}

make_reference_row <- function(gam) {
  # Single "reference" observation for predict(): factors -> first level,
  # numerics -> median from var.summary.
  vs <- gam$var.summary
  ref <- list()
  for (nm in names(vs)) {
    v <- vs[[nm]]
    if (is.factor(v)) {
      ref[[nm]] <- factor(levels(v)[1], levels = levels(v))
    } else if (is.ordered(v)) {
      ref[[nm]] <- ordered(levels(v)[1], levels = levels(v))
    } else {
      ref[[nm]] <- median(v, na.rm = TRUE)
    }
  }
  if ("s" %in% names(ref)) ref[["s"]] <- 0   # zero out offset column
  # do.call avoids incremental data.frame assignment issues
  do.call(data.frame, c(ref, list(stringsAsFactors = FALSE)))
}

get_smooth_range <- function(smooth_obj, gam) {
  term <- smooth_obj$term
  bounds <- extract_bounds_from_term(term)
  vs <- gam$var.summary
  # data range for the unwrapped (clean) variable
  clean <- extract_clean_var(term)
  if (clean %in% names(vs)) {
    vals <- vs[[clean]]
    data_lo <- min(vals, na.rm = TRUE)
    data_hi <- max(vals, na.rm = TRUE)
  } else if (term %in% names(vs)) {
    vals <- vs[[term]]
    data_lo <- min(vals, na.rm = TRUE)
    data_hi <- max(vals, na.rm = TRUE)
  } else {
    data_lo <- 0; data_hi <- 1
  }
  lo <- if (!is.na(bounds$lo)) bounds$lo else data_lo
  hi <- if (!is.na(bounds$hi)) bounds$hi else data_hi
  if (lo >= hi) { lo <- data_lo; hi <- data_hi }
  list(lo = lo, hi = hi)
}

# ============== Main Dump ==============

load_model_obj <- function(rdata_path) {
  if (grepl("\\.rds$", rdata_path, ignore.case = TRUE)) {
    m <- readRDS(rdata_path)
  } else {
    env <- new.env()
    load(rdata_path, envir = env)
    obj_names <- ls(env)
    if ("model_package" %in% obj_names) {
      m <- env$model_package
    } else {
      m <- get(obj_names[1], envir = env)
    }
  }
  gam <- m$MODEL
  if (is.null(gam)) stop(paste("No MODEL element in", rdata_path))
  # strip bam discrete info -> avoids contrasts error in older mgcv
  if (!is.null(gam$dinfo)) {
    gam$dinfo <- NULL
    class(gam) <- c("gam", "glm", "lm")
  }
  gam
}

dump_smooth_terms <- function(gam, ref_row, to_status_label, n_grid = 200) {
  # smooth-term rows via predict(type="terms") on an n_grid sweep of each var
  rows <- list()
  add_row <- function(vn1, vv1, vn2, vv2, val) {
    rows[[length(rows) + 1]] <<- data.frame(
      model = to_status_label, var_name1 = vn1,
      var_val1 = as.character(vv1),
      var_name2 = if (is.na(vn2)) NA_character_ else as.character(vn2),
      var_val2 = if (is.na(vv2)) NA_character_ else as.character(vv2),
      value = as.numeric(val), stringsAsFactors = FALSE
    )
  }

  term_names <- colnames(predict(gam, newdata = ref_row, type = "terms"))

  for (s in gam$smooth) {
    term_label <- s$term
    clean_var <- extract_clean_var(term_label)
    rng <- get_smooth_range(s, gam)
    grid <- seq(rng$lo, rng$hi, length.out = n_grid)
    by_var_raw <- s$by
    has_by <- !is.null(by_var_raw) && !is.na(by_var_raw) && by_var_raw != "NA"
    by_var <- if (has_by) unwrap_formula(by_var_raw) else by_var_raw

    pred_col <- s$label
    col_idx <- which(term_names == pred_col)
    if (length(col_idx) == 0) col_idx <- grep(pred_col, term_names, fixed = TRUE)
    if (length(col_idx) == 0) {
      cat(sprintf("    WARNING: could not find predict column for %s, skipping\n", pred_col))
      next
    }
    col_idx <- col_idx[1]

    nd <- ref_row[rep(1, n_grid), , drop = FALSE]
    rownames(nd) <- NULL

    if (clean_var %in% names(nd)) {
      nd[[clean_var]] <- grid
    } else if (term_label %in% names(nd)) {
      nd[[term_label]] <- grid
    } else {
      cat(sprintf("    WARNING: variable %s not in model data, skipping\n", clean_var))
      next
    }

    if (is_factor_by(s)) {
      by_level <- trimws(s$by.level)
      # Use clean name for data frame column lookup
      if (by_var %in% names(nd)) {
        lvls <- levels(gam$var.summary[[by_var]])
        nd[[by_var]] <- factor(rep(by_level, n_grid), levels = lvls)
      } else if (by_var_raw %in% names(nd)) {
        lvls <- levels(gam$var.summary[[by_var_raw]])
        nd[[by_var_raw]] <- factor(rep(by_level, n_grid), levels = lvls)
      }
    }
    if (is_numeric_by(s)) {
      if (is_ordered_by(s)) {
        # ordered(v_flag) — set to ordered factor with by.level active
        by_level <- trimws(s$by.level)
        col <- if (by_var %in% names(nd)) by_var else by_var_raw
        vs_entry <- gam$var.summary[[col]]
        if (is.ordered(vs_entry)) {
          nd[[col]] <- ordered(rep(by_level, n_grid), levels = levels(vs_entry))
        } else {
          nd[[col]] <- rep(1.0, n_grid)
        }
      } else {
        if (by_var %in% names(nd)) {
          nd[[by_var]] <- rep(1.0, n_grid)
        } else if (by_var_raw %in% names(nd)) {
          nd[[by_var_raw]] <- rep(1.0, n_grid)
        }
      }
    }

    pred <- predict(gam, newdata = nd, type = "terms")
    y <- pred[, col_idx]

    if (!has_by) {
      for (i in seq_along(grid)) add_row(clean_var, grid[i], NA, NA, y[i])
    } else if (is_factor_by(s)) {
      by_level <- trimws(s$by.level)
      for (i in seq_along(grid)) add_row(clean_var, grid[i], by_var, by_level, y[i])
    } else {
      for (i in seq_along(grid)) add_row(clean_var, grid[i], by_var, NA, y[i])
    }
  }

  if (length(rows) > 0) do.call(rbind, rows) else NULL
}

dump_one_model <- function(rdata_path, to_status_label, stacked_paths = NULL, n_grid = 200) {
  gam <- load_model_obj(rdata_path)
  coefs <- gam$coefficients
  ref_row <- make_reference_row(gam)
  rows <- list()

  add_row <- function(vn1, vv1, vn2, vv2, val) {
    rows[[length(rows) + 1]] <<- data.frame(
      model = to_status_label, var_name1 = vn1,
      var_val1 = as.character(vv1),
      var_name2 = if (is.na(vn2)) NA_character_ else as.character(vn2),
      var_val2 = if (is.na(vv2)) NA_character_ else as.character(vv2),
      value = as.numeric(val), stringsAsFactors = FALSE
    )
  }

  # --- 1. Intercept (base) ---
  intercept <- coefs["(Intercept)"]
  pterms <- attr(gam$pterms, "term.labels")   # kept for the summary line at the bottom

  # --- 2. Parametric factor terms — accumulate base + stack into one row per (var, level)
  param_acc <- new.env(hash = TRUE)
  # Accumulate one (var1,level1[,var2,level2]) coefficient into param_acc, summing
  # if the key already exists (base + stacked layers share the map).
  acc_one <- function(key, vn1, vv1, vn2, vv2, val) {
    if (exists(key, envir = param_acc, inherits = FALSE)) {
      old <- get(key, envir = param_acc)
      val <- old$value + val
    }
    assign(key, list(var_name = vn1, level = vv1, var_name2 = vn2,
                     level2 = vv2, value = val), envir = param_acc)
  }
  accum_parametrics <- function(g) {
    cf <- g$coefficients
    pt <- attr(g$pterms, "term.labels")
    is_inter <- grepl(":", pt, fixed = TRUE)
    claimed <- character(0)

    # 1) Interaction terms first. The term label carries the exact factor names
    #    on each side of ':', so split the coef name (f1<l1>:f2<l2>) and strip
    #    each known factor name — no prefix guessing, robust to a factor that
    #    only appears inside an interaction (e.g. months_in_current_bkt).
    for (term in pt[is_inter]) {
      facs <- strsplit(term, ":", fixed = TRUE)[[1]]
      if (length(facs) != 2) next                 # only 2-way interactions handled
      f1 <- facs[1]; f2 <- facs[2]
      for (cn in setdiff(names(cf), c("(Intercept)", claimed))) {
        if (!grepl(":", cn, fixed = TRUE)) next
        seg <- strsplit(cn, ":", fixed = TRUE)[[1]]
        if (length(seg) != 2) next
        if (!startsWith(seg[1], f1) || !startsWith(seg[2], f2)) next
        l1 <- substring(seg[1], nchar(f1) + 1)
        l2 <- substring(seg[2], nchar(f2) + 1)
        if (nchar(l1) == 0 || nchar(l2) == 0) next
        claimed <- c(claimed, cn)
        acc_one(paste(f1, l1, f2, l2, sep = "|"), f1, l1, f2, l2, unname(cf[cn]))
      }
    }

    # 2) Main-effect terms, longest name first so nested names (e.g. "month" vs
    #    "months_in_current_bkt") don't steal each other's coefs; skip any coef
    #    containing ':' (already claimed by an interaction above).
    mains <- pt[!is_inter]
    mains <- mains[order(-nchar(mains))]
    for (var_name in mains) {
      pattern <- paste0("^", gsub("([.()\\[\\]])", "\\\\\\1", var_name))
      matching <- setdiff(grep(pattern, names(cf), value = TRUE),
                          c("(Intercept)", claimed))
      for (cn in matching) {
        if (grepl(":", cn, fixed = TRUE)) next
        level <- sub(pattern, "", cn)
        if (nchar(level) == 0) next
        claimed <- c(claimed, cn)
        acc_one(paste0(var_name, "|", level), var_name, level, NA, NA, unname(cf[cn]))
      }
    }
  }
  accum_parametrics(gam)

  # --- 3. Smooth terms (base) ---
  smooth_df <- dump_smooth_terms(gam, ref_row, to_status_label, n_grid)
  n_smooth_base <- length(gam$smooth)
  n_smooth_stacked <- 0

  # --- 4. Stacked layers — consolidate intercept + append smooths + accumulate parametrics
  if (!is.null(stacked_paths)) {
    for (sp in stacked_paths) {
      cat(sprintf("    + stacked: %s\n", basename(sp)))
      sgam <- load_model_obj(sp)

      # Add stacked intercept to base
      s_intercept <- sgam$coefficients["(Intercept)"]
      if (!is.na(s_intercept)) {
        intercept <- intercept + s_intercept
        cat(sprintf("      intercept += %.6f (combined = %.6f)\n", s_intercept, intercept))
      }

      # Accumulate stacked parametric (categorical) coefs into the same map as base
      accum_parametrics(sgam)

      # Build reference row for stacked model (offset = 0)
      s_ref <- make_reference_row(sgam)
      if (!(".base_logit" %in% names(s_ref))) s_ref[[".base_logit"]] <- 0

      # Dump stacked smooth terms
      s_smooth_df <- dump_smooth_terms(sgam, s_ref, to_status_label, n_grid)
      if (!is.null(s_smooth_df)) {
        smooth_df <- rbind(smooth_df, s_smooth_df)
        n_smooth_stacked <- n_smooth_stacked + length(sgam$smooth)
        cat(sprintf("      %d smooth terms appended\n", length(sgam$smooth)))
      }
    }
  }

  # --- Emit accumulated parametrics (interactions carry var2/level2) ---
  for (key in ls(param_acc)) {
    p <- get(key, envir = param_acc)
    add_row(p$var_name, p$level, p$var_name2, p$level2, p$value)
  }

  # --- Write intercept row (consolidated) ---
  add_row("intercept", "intercept", NA, NA, intercept)

  df <- do.call(rbind, rows)
  if (!is.null(smooth_df)) df <- rbind(df, smooth_df)

  list(coef_df = df, n_smooth = n_smooth_base + n_smooth_stacked,
       n_parametric = length(pterms), formula = gam$formula,
       n_stacked = length(if (is.null(stacked_paths)) list() else stacked_paths))
}

dump_from_state <- function(model_configs, output_path) {
  all_dfs <- list()
  for (cfg in model_configs) {
    stacked <- cfg$stacked
    has_stacked <- !is.null(stacked) && length(stacked) > 0
    label <- if (has_stacked) paste0(basename(cfg$path), " + ", length(stacked), " stacked") else basename(cfg$path)
    cat(sprintf("  Dumping: %s -> %s\n", label, cfg$to_status))
    result <- dump_one_model(cfg$path, cfg$to_status, stacked_paths = stacked)
    all_dfs[[length(all_dfs) + 1]] <- result$coef_df
    cat(sprintf("    %d rows (%d smooth, %d parametric terms)\n",
        nrow(result$coef_df), result$n_smooth, result$n_parametric))
  }
  combined <- do.call(rbind, all_dfs)
  write.table(combined, output_path, sep = "\t", row.names = FALSE, quote = FALSE, na = "")
  cat(sprintf("  Wrote: %s (%d rows)\n", output_path, nrow(combined)))
}

# ============== Execute ==============
# Usage: Rscript dump_gam_to_coef.R <output_file> <base_path> <to_status> [+stacked_path ...] [...]
# Stacked layers are prefixed with "+", follow their base model's to_status.
# Example:
#   Rscript dump_gam_to_coef.R out.txt base.RData D1M +stacked.RData base2.RData PIF

if (!interactive() && !exists(".sourced_as_lib")) {

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 3) stop("Usage: Rscript dump_gam_to_coef.R <output_file> <base_path> <to_status> [+stacked ...] [...]")

output_path <- args[1]
dir.create(dirname(output_path), recursive = TRUE, showWarnings = FALSE)

model_configs <- list()
i <- 2
while (i <= length(args)) {
  base_path <- args[i]
  to_status <- args[i + 1]
  i <- i + 2
  stacked <- c()
  while (i <= length(args) && grepl("^\\+", args[i])) {
    stacked <- c(stacked, sub("^\\+", "", args[i]))
    i <- i + 1
  }
  cfg <- list(path = base_path, to_status = to_status)
  if (length(stacked) > 0) cfg$stacked <- stacked
  model_configs[[length(model_configs) + 1]] <- cfg
}

dump_from_state(model_configs, output_path)

}  # end if (!interactive())

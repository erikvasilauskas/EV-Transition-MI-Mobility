
# ---- staffing_patterns_wide_per_segment.R  ----
library(readxl)
library(dplyr)
library(tidyr)
library(janitor)
library(purrr)
library(stringr)
library(writexl)
library(tibble)

# Set working directory
setwd("C:/Users/vasilauskas/W.E. Upjohn Institute/Electric Vehicles - Documents/_EV Workforce Hub/MCDA, CAR Data Inputs, 10 Category Supply Chain Framework")


xlsx_path <- "Staffing Patterns for 10 Categories.xlsx"
out_path  <- "Staffing_Patterns_Wide_By_Segment_with_EP.xlsx"
ep<-read.csv("Employment Projections.csv")


# --- Helpers ---
normalize_cols <- function(df) {
  df %>%
    clean_names() %>%
    rename(
      occcd     = any_of(c("occcd", "occ_code", "occ", "occ_cd")),
      soctitle  = any_of(c("soctitle", "soc_title", "occupation_title")),
      estyear   = any_of(c("estyear", "est_year", "year", "est_yr")),
      roundempl = any_of(c("roundempl", "rounded_employment", "employment", "empl"))
    )
}

sanitize_sheetname <- function(x) {
  x %>%
    str_replace_all("[\\[\\]\\:\\*\\?/\\\\]", " ") %>%
    str_squish() %>%
    str_trunc(31, ellipsis = "")
}

sheets <- excel_sheets(xlsx_path)

# --- Read & combine ---
raw_list <- map(
  sheets,
  ~ read_excel(xlsx_path, sheet = .x) %>%
    normalize_cols() %>%
    mutate(segment = .x)
)

df_long <- bind_rows(raw_list) %>%
  filter(!is.na(occcd), !is.na(estyear)) %>%
  mutate(estyear = as.integer(estyear))

# Identify metadata columns (everything except these)
meta_cols <- setdiff(names(df_long), c("segment", "estyear", "roundempl", "occcd"))

# --- Preferred metadata by occcd ---
meta_2024 <- df_long %>%
  filter(estyear == 2024) %>%
  arrange(occcd) %>%
  group_by(occcd) %>%
  slice(1) %>%
  ungroup() %>%
  select(occcd, all_of(meta_cols))

missing_2024_occs <- setdiff(unique(df_long$occcd), unique(meta_2024$occcd))
meta_rest <- setdiff(meta_cols, "soctitle")

# FIXED: safely create missing metadata cols as NA when only soctitle is backfilled
fallback_soctitle <- df_long %>%
  filter(occcd %in% missing_2024_occs) %>%
  arrange(occcd, desc(estyear)) %>%                   # most recent first
  group_by(occcd) %>%
  summarize(
    soctitle = dplyr::first(soctitle[!is.na(soctitle)], default = NA_character_),
    .groups = "drop"
  ) %>%
  add_column(
    !!!setNames(
      rep(list(NA), length(meta_rest)),   # will recycle NA and coerce types on bind_rows
      meta_rest
    )
  )

metadata_by_occcd <- bind_rows(meta_2024, fallback_soctitle) %>%
  distinct(occcd, .keep_all = TRUE)

# --- Pivot wider within each segment ---
empl_wide <- df_long %>%
  select(segment, occcd, estyear, roundempl) %>%
  distinct() %>%
  pivot_wider(
    id_cols = c(segment, occcd),
    names_from = estyear,
    values_from = roundempl,
    names_prefix = "empl_"
  )

# Make sure the year columns we need exist even if a segment lacks them
for (yr in c(2021, 2024)) {
  nm <- paste0("empl_", yr)
  if (!nm %in% names(empl_wide)) empl_wide[[nm]] <- NA_real_
}


# --- Attach metadata, SOC level, arrange columns ---
result_all <- empl_wide %>%
  left_join(metadata_by_occcd, by = "occcd") %>%
  mutate(
    occ_str = as.character(occcd),
    occ_level = dplyr::case_when(
      str_detect(occ_str, "^\\d{2}-0000$") | str_detect(occ_str, "^\\d{2}0000$") ~ "major",
      str_detect(occ_str, "^\\d{2}-\\d{2}00(\\.\\d{2})?$") | str_detect(occ_str, "^\\d{4}00$") ~ "broad",
      str_detect(occ_str, "^\\d{2}-\\d{4}\\.\\d{2}$") ~ "detailed",
      str_detect(occ_str, "^\\d{2}-\\d{4}$") | str_detect(occ_str, "^\\d{6}$") ~ "detailed",
      TRUE ~ "unknown"
    ),
    # Flag “Total, all occupations”
    is_total_all = str_detect(occ_str, "^(00-0000)(\\.00)?$") | str_detect(occ_str, "^0{6}$")
  ) %>%
  select(-occ_str) %>%
  relocate(segment, occcd, occ_level, soctitle, .before = everything()) %>%
  group_by(segment, occ_level) %>%
  mutate(
    .denom_2021 = if_else(
      occ_level %in% c("major","detailed"),
      sum(if_else(!is_total_all, empl_2021, 0), na.rm = TRUE),
      NA_real_
    ),
    .denom_2024 = if_else(
      occ_level %in% c("major","detailed"),
      sum(if_else(!is_total_all, empl_2024, 0), na.rm = TRUE),
      NA_real_
    )
  ) %>%
  ungroup() %>%
  mutate(
    # Shares (exclude 00-0000 from majors; detailed has no “total” row but keep symmetry)
    pct_seg_major_2021 = dplyr::case_when(
      occ_level == "major" & !is_total_all ~ if_else(.denom_2021 > 0, empl_2021 / .denom_2021, NA_real_),
      occ_level == "major" &  is_total_all ~ NA_real_,
      TRUE ~ NA_real_
    ),
    pct_seg_detailed_2021 = dplyr::case_when(
      occ_level == "detailed" ~ if_else(.denom_2021 > 0, empl_2021 / .denom_2021, NA_real_),
      TRUE ~ NA_real_
    ),
    pct_seg_major_2024 = dplyr::case_when(
      occ_level == "major" & !is_total_all ~ if_else(.denom_2024 > 0, empl_2024 / .denom_2024, NA_real_),
      occ_level == "major" &  is_total_all ~ NA_real_,
      TRUE ~ NA_real_
    ),
    pct_seg_detailed_2024 = dplyr::case_when(
      occ_level == "detailed" ~ if_else(.denom_2024 > 0, empl_2024 / .denom_2024, NA_real_),
      TRUE ~ NA_real_
    )
  ) %>%
  select(-.denom_2021, -.denom_2024) %>%
  # ---- 2021→2024 changes (compute BEFORE relocating) ----
mutate(
  level_change_2021_2024 = if_else(
    !is.na(empl_2021) & !is.na(empl_2024), empl_2024 - empl_2021, NA_real_
  ),
  pct_change_2021_2024 = dplyr::case_when(
    !is.na(empl_2021) & empl_2021 != 0 & !is.na(empl_2024) ~ (empl_2024 / empl_2021 - 1) * 100,
    TRUE ~ NA_real_
  )
)

# ---------------- Column ordering with relocate() ----------------
result_all <- result_all %>%
  {
    # Find the last employment column (e.g., empl_2024)
    last_empl <- grep("^empl_\\d{4}$", names(.), value = TRUE) |> sort() |> tail(1)
    
    # 1) Move ALL pct_seg_*_YYYY columns right after the last empl_YYYY
    . <- relocate(
      .,
      matches("^pct_seg_(major|detailed)_\\d{4}$"),
      .after = dplyr::all_of(last_empl)
    )
    
    # 2) Move change columns right after the pct block
    . <- relocate(
      .,
      dplyr::any_of(c("level_change_2021_2024", "pct_change_2021_2024")),
      .after = matches("^pct_seg_(major|detailed)_\\d{4}$")
    )
    
    .
  }

# --- Attach Employment Projections (EP) with snake names & reduced edu group ---

# 1) Clean EP names to snake_case
ep_clean <- ep %>% janitor::clean_names()

# 2) Helper to coalesce the first present column from a set of aliases
pick_first <- function(df, candidates) {
  hits <- intersect(candidates, names(df))
  if (length(hits) == 0) return(NA_character_)
  df[[hits[1]]]
}

# 3) Build a standardized projections subset (keep merge key as-is; no SOC reformat)
proj_subset <- tibble::tibble(
  # merge key (use best-available alias; do not reformat)
  occcd = pick_first(ep_clean, c("occcd","occ_code","soc_code","occupation_code","occ_cd","soc")),
  
  entry_education = pick_first(ep_clean, c("entry_education","typical_entry_level_education")),
  edu_code = pick_first(ep_clean, c("edu_code","education_code")),
  related_work_experience = pick_first(ep_clean, c("related_work_experience","work_experience_in_a_related_occupation")),
  workex_code = pick_first(ep_clean, c("workex_code","work_experience_code")),
  on_the_job_training = pick_first(ep_clean, c("on_the_job_training","typical_on_the_job_training")),
  training_code = pick_first(ep_clean, c("training_code","trcode","tr_code"))
) %>%
  # 4) Reduced education buckets
  dplyr::mutate(
    edu_grouped = dplyr::case_when(
      entry_education %in% c(
        "No formal educational credential",
        "High school diploma or equivalent"
      ) ~ "HS or less",
      entry_education %in% c(
        "Postsecondary nondegree award",
        "Associate's degree",
        "Some college, no degree"
      ) ~ "SC or associate's",
      entry_education %in% c(
        "Bachelor's degree",
        "Master's degree",
        "Doctoral or professional degree"
      ) ~ "BA+",
      TRUE ~ NA_character_
    )
  ) %>%
  # 5) Prefix all EP fields except the join key
  dplyr::rename_with(~ paste0("ep_", .x), .cols = -occcd)

# 6) Join EP to your result_all (detailed-only rule applied after join)
result_joined <- result_all %>%
  dplyr::left_join(proj_subset, by = "occcd")

# 7) Force EP fields to NA for non-detailed rows
ep_cols <- grep("^ep_", names(result_joined), value = TRUE)
if (length(ep_cols)) {
  result_joined <- result_joined %>%
    dplyr::mutate(
      dplyr::across(
        dplyr::all_of(ep_cols),
        ~ dplyr::if_else(occ_level == "detailed", ., NA),
        .names = "{.col}"
      )
    )
}

# 8) Merge diagnostics for detailed occupations
if (length(ep_cols)) {
  n_total_detailed <- sum(result_joined$occ_level == "detailed", na.rm = TRUE)
  n_ep_attached <- sum(
    result_joined$occ_level == "detailed" &
      rowSums(!is.na(result_joined[, ep_cols, drop = FALSE])) > 0,
    na.rm = TRUE
  )
  merge_rate <- if (n_total_detailed > 0) n_ep_attached / n_total_detailed else NA_real_
  message(
    sprintf("EP merge (detailed): %s of %s (%.1f%%)",
            n_ep_attached, n_total_detailed, 100 * merge_rate)
  )
}

# ---- from here on, use `result_joined` instead of `result_all` ----


# --- Split by segment, preserve input order ---
segments_in_order <- unique(result_joined$segment) %>%
  factor(levels = sheets) %>%
  as.character()

sheet_list <- map(segments_in_order, function(seg) {
  result_joined %>%
    filter(segment == seg) %>%
    select(-segment) %>%
    arrange(occcd)
})
names(sheet_list) <- sanitize_sheetname(segments_in_order)

# # --- Write out ---
# write_xlsx(sheet_list, path = out_path)
# message("Exported: ", out_path)

# --- Write three separate workbooks: All, Major-only, Detailed-only ---

make_sheet_name <- function(base) sanitize_sheetname(base)

# Derive output paths from your existing out_path
out_all      <- out_path
out_major    <- if (grepl("\\.xlsx$", out_path, ignore.case = TRUE)) {
  sub("\\.xlsx$", "_MAJOR.xlsx", out_path, ignore.case = TRUE)
} else paste0(out_path, "_MAJOR.xlsx")

out_detailed <- if (grepl("\\.xlsx$", out_path, ignore.case = TRUE)) {
  sub("\\.xlsx$", "_DETAILED.xlsx", out_path, ignore.case = TRUE)
} else paste0(out_path, "_DETAILED.xlsx")

segments_in_order <- unique(result_joined$segment) %>%
  factor(levels = sheets) %>%
  as.character()

# Helper to build a workbook's sheet list given a filter on occ_level
build_sheet_list <- function(df, level = c("all","major","detailed")) {
  level <- match.arg(level)
  sheet_list <- list()
  
  for (seg in segments_in_order) {
    df_seg <- df %>%
      dplyr::filter(segment == seg) %>%
      dplyr::select(-segment)
    
    df_out <- switch(
      level,
      all      = df_seg %>% dplyr::arrange(occcd),
      major    = df_seg %>% dplyr::filter(occ_level == "major")    %>% dplyr::arrange(dplyr::desc(empl_2024), occcd),
      detailed = df_seg %>% dplyr::filter(occ_level == "detailed") %>% dplyr::arrange(dplyr::desc(empl_2024), occcd)
    )
    
    # Skip empty sheets (e.g., if a segment has no majors)
    if (nrow(df_out) > 0) {
      sheet_list[[ make_sheet_name(seg) ]] <- df_out
    }
  }
  
  sheet_list
}

# Build and write each workbook
sheet_list_all      <- build_sheet_list(result_joined, level = "all")
sheet_list_major    <- build_sheet_list(result_joined, level = "major")
sheet_list_detailed <- build_sheet_list(result_joined, level = "detailed")

# Write files (only if there is at least one non-empty sheet)
if (length(sheet_list_all))      writexl::write_xlsx(sheet_list_all,      path = out_all)
if (length(sheet_list_major))    writexl::write_xlsx(sheet_list_major,    path = out_major)
if (length(sheet_list_detailed)) writexl::write_xlsx(sheet_list_detailed, path = out_detailed)

message("Exported: ",
        paste(c(
          if (length(sheet_list_all))      out_all      else NULL,
          if (length(sheet_list_major))    out_major    else NULL,
          if (length(sheet_list_detailed)) out_detailed else NULL
        ), collapse = " | "))

# --- 4) LONG workbook: one sheet with segment column and all rows long ---

# Output path for the long workbook
out_long <- if (grepl("\\.xlsx$", out_path, ignore.case = TRUE)) {
  sub("\\.xlsx$", "_LONG.xlsx", out_path, ignore.case = TRUE)
} else paste0(out_path, "_LONG.xlsx")

# Reuse the same SOC-level classifier
classify_level <- function(x) {
  x <- as.character(x)
  dplyr::case_when(
    stringr::str_detect(x, "^\\d{2}-0000$") | stringr::str_detect(x, "^\\d{2}0000$") ~ "major",
    stringr::str_detect(x, "^\\d{2}-\\d{2}00(\\.\\d{2})?$") | stringr::str_detect(x, "^\\d{4}00$") ~ "broad",
    stringr::str_detect(x, "^\\d{2}-\\d{4}\\.\\d{2}$") ~ "detailed",
    stringr::str_detect(x, "^\\d{2}-\\d{4}$") | stringr::str_detect(x, "^\\d{6}$") ~ "detailed",
    TRUE ~ "unknown"
  )
}

# Build a clean long table:
# - segment, occcd, soctitle, occ_level
# - estyear, roundempl (employment)
# - ep_* columns (detailed-only after join)
long_all <- df_long %>%
  dplyr::select(segment, occcd, estyear, roundempl) %>%
  dplyr::left_join(metadata_by_occcd %>% dplyr::select(occcd, soctitle), by = "occcd") %>%
  dplyr::mutate(occ_level = classify_level(occcd)) %>%
  # join projections subset (already prefixed ep_* except key)
  dplyr::left_join(proj_subset, by = "occcd")

# Force ep_ fields to NA for non-detailed rows (same rule as wide)
ep_cols_long <- grep("^ep_", names(long_all), value = TRUE)
if (length(ep_cols_long)) {
  long_all <- long_all %>%
    dplyr::mutate(
      dplyr::across(
        dplyr::all_of(ep_cols_long),
        ~ dplyr::if_else(occ_level == "detailed", ., NA),
        .names = "{.col}"
      )
    )
}

# Nice ordering
long_all <- long_all %>%
  dplyr::arrange(segment, occ_level, occcd, estyear) %>%
  dplyr::relocate(segment, occcd, soctitle, occ_level, estyear, roundempl)

# Write a single-sheet workbook
if (nrow(long_all) > 0) {
  writexl::write_xlsx(list("All (Long)" = long_all), path = out_long)
  message("Exported: ", out_long)
}

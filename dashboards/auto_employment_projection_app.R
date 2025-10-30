library(shiny)
library(dplyr)
library(readr)
library(tidyr)
library(DT)

# Paths
repo_root <- normalizePath("..", mustWork = FALSE)
share_path <- file.path(repo_root, "data", "intermediate", "auto_share_comparison.csv")
projection_path <- file.path(repo_root, "data", "intermediate", "employment_projection_comparison.csv")

shares_raw <- read_csv(share_path, show_col_types = FALSE)
projections_raw <- read_csv(projection_path, show_col_types = FALSE)

share_choices <- c(
  "SAM (auto_share)" = "sam_auto_share",
  "Lightcast" = "lightcast_share",
  "BEA Summary (Total Output)" = "bea_summary_total_output_share",
  "BEA Detail (Intermediate Inputs)" = "bea_detail_intermediate_share",
  "BEA Detail (Total Output)" = "bea_detail_total_output_share",
  "MRIO Indirect" = "mrio_indirect_share",
  "MRIO Total" = "mrio_total_share"
)

projection_choices <- c(
  "Moody's Michigan" = "moodys_mi_pct_change_2024_2030_employment",
  "Moody's US" = "moodys_us_pct_change_2024_2030_employment",
  "DTMB Michigan" = "mi_dtmb_six_year_rate",
  "BLS US" = "bls_us_six_year_employment_rate_change"
)

oem_naics <- c("5413", "5414", "5417")

ui <- fluidPage(
  titlePanel("Automotive Employment Projection Explorer"),
  sidebarLayout(
    sidebarPanel(
      selectInput("share_choice", "Auto-attribution share source:", choices = share_choices, selected = "sam_auto_share"),
      selectInput("projection_choice", "Employment projection rate source:", choices = projection_choices, selected = "moodys_mi_pct_change_2024_2030_employment"),
      helpText("Shares apply only to upstream industries and NAICS 5413, 5414, 5417. All other industries retain 100% of QCEW base employment before projections.")
    ),
    mainPanel(
      tabsetPanel(
        tabPanel("Table", DTOutput("projection_table")),
        tabPanel("Summary Plot", plotOutput("projection_plot", height = "600px"))
      )
    )
  )
)

server <- function(input, output, session) {
  projection_data <- reactive({
    share_col <- input$share_choice
    rate_col <- input$projection_choice

    share_label <- names(share_choices[share_choices == share_col])
    projection_label <- names(projection_choices[projection_choices == rate_col])

    shares <- shares_raw %>%
      select(naics_code, naics_title, segment_id, segment_name, stage, employment_qcew_2024 = employment_qcew_2024, share_value = all_of(share_col))

    projections <- projections_raw %>%
      select(naics_code, employment_qcew_2024_proj = employment_qcew_2024, rate_value = all_of(rate_col))

    combined <- shares %>%
      left_join(projections, by = c("naics_code")) %>%
      mutate(
        share_value = coalesce(share_value, 0),
        stage_lower = tolower(stage),
        share_applied = if_else(stage_lower == "upstream" | naics_code %in% oem_naics, share_value, 1),
        base_employment = coalesce(employment_qcew_2024_proj, employment_qcew_2024),
        projection_rate = coalesce(rate_value, 0),
        auto_attributed_employment = round(base_employment * share_applied),
        projected_employment = round(auto_attributed_employment * (1 + projection_rate)),
        share_source = share_label,
        projection_source = projection_label
      ) %>%
      select(
        naics_code,
        naics_title,
        segment_id,
        segment_name,
        stage,
        base_employment,
        share_applied,
        projection_rate,
        auto_attributed_employment,
        projected_employment
      )

    combined
  })

  output$projection_table <- renderDT({
    datatable(
      projection_data(),
      options = list(pageLength = 25),
      rownames = FALSE
    )
  })

  output$projection_plot <- renderPlot({
    df <- projection_data()
    df <- df %>%
      mutate(label = paste(segment_name, naics_code, sep = " - "))

    barplot(
      df$projected_employment,
      names.arg = df$naics_code,
      las = 2,
      col = "steelblue",
      main = "Projected Employment by NAICS",
      ylab = "Projected Employment",
      cex.names = 0.7
    )
  })
}

shinyApp(ui = ui, server = server)

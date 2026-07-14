# Workflow Diagram

```mermaid
flowchart LR
  A["Lead source: Gmail, form, chat, referral"] --> B["Webhook-style intake endpoint"]
  B --> C["Contact extraction"]
  C --> D["AI-style lead analysis"]
  D --> E["Priority scoring: Hot, Warm, Cold"]
  E --> F["Mini CRM storage"]
  F --> G["Dashboard"]
  F --> H["CSV export"]
  F --> I["Automation logs"]
  E --> J["Follow-up date and next action"]
```

## Notes

The demo uses a local Python server and JSON storage, but the same workflow can be connected to HubSpot, GoHighLevel, Pipedrive, Airtable, Google Sheets, Zapier, Make, or n8n.

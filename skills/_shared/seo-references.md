# SEO Reference Data

## CTR Benchmarks by Position

| Position | Desktop | Mobile   |
| -------- | ------- | -------- |
| 1        | 28-32%  | 24-28%   |
| 2        | 14-18%  | 12-15%   |
| 3        | 9-12%   | 8-10%    |
| 4-5      | 5-8%    | 4-6%     |
| 6-10     | 2-5%    | 1.5-4%   |
| 11-20    | 1-2%    | 0.5-1.5% |

## Framework Meta Tag Patterns

### Next.js App Router

```tsx
export const metadata: Metadata = {
  title: "Title",
  description: "Desc",
  openGraph: { title: "OG", images: ["/og.png"] },
};
// Dynamic: export async function generateMetadata({ params })
```

### Next.js Pages Router

```tsx
<Head>
  <title>Title</title>
  <meta name="description" content="..." />
</Head>
```

### React Helmet

```tsx
<Helmet>
  <title>Title</title>
  <meta name="description" content="..." />
</Helmet>
```

## Structured Data Templates

### Article

```json
{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "Title",
  "author": { "@type": "Person", "name": "Name" },
  "datePublished": "2026-01-15"
}
```

### Product

```json
{
  "@context": "https://schema.org",
  "@type": "Product",
  "name": "Name",
  "offers": { "@type": "Offer", "price": "29", "priceCurrency": "USD" }
}
```

### FAQ

```json
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "Q?",
      "acceptedAnswer": { "@type": "Answer", "text": "A" }
    }
  ]
}
```

### TouristTrip (tours, adventures, travel)

```json
{
  "@context": "https://schema.org",
  "@type": "TouristTrip",
  "name": "Trip Name",
  "description": "Trip description",
  "touristType": "Adventure Travel",
  "itinerary": {
    "@type": "ItemList",
    "itemListElement": [
      { "@type": "ListItem", "position": 1, "name": "Day 1: Arrival" }
    ]
  },
  "provider": {
    "@type": "TourOperator",
    "name": "Company Name",
    "url": "https://example.com"
  },
  "offers": {
    "@type": "Offer",
    "price": "5000",
    "priceCurrency": "USD",
    "availability": "https://schema.org/InStock"
  }
}
```

### LocalBusiness (service companies, agencies)

```json
{
  "@context": "https://schema.org",
  "@type": "LocalBusiness",
  "name": "Business Name",
  "url": "https://example.com",
  "telephone": "+1-555-000-0000",
  "address": {
    "@type": "PostalAddress",
    "addressLocality": "City",
    "addressRegion": "State",
    "addressCountry": "US"
  }
}
```

### HowTo (guides, tutorials, workout instructions)

```json
{
  "@context": "https://schema.org",
  "@type": "HowTo",
  "name": "How to Do Something",
  "step": [
    {
      "@type": "HowToStep",
      "name": "Step 1",
      "text": "Do this first"
    }
  ]
}
```

### Breadcrumb

```json
{
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  "itemListElement": [
    {
      "@type": "ListItem",
      "position": 1,
      "name": "Home",
      "item": "https://example.com"
    }
  ]
}
```

## GSC File Patterns

| Pattern          | Contains         |
| ---------------- | ---------------- |
| `Queries*.csv`   | Search queries   |
| `Pages*.csv`     | Page performance |
| `Devices*.csv`   | Device breakdown |
| `Countries*.csv` | Geo distribution |
| `Chart*.csv`     | Daily trends     |

Note: Also supports localized column names (auto-detected).

## Analytics Benchmarks

Industry-average benchmarks for comparison in `/cs-analytics` reports.

### Conversion Rates

| Metric                        | Typical Range | Source Context              |
| ----------------------------- | ------------- | --------------------------- |
| Form completion (simple)      | 30-50%        | 3-5 fields, no login       |
| Form completion (complex)     | 15-25%        | 6+ fields, multi-step      |
| E-commerce cart → purchase    | 25-45%        | Varies by price point       |
| Newsletter signup (sitewide)  | 1-3%          | Visible CTA, value prop     |
| Newsletter signup (blog only) | 2-5%          | Content-relevant offer      |
| Contact form submission       | 10-20%        | Simple form, visible        |
| Landing page → key event      | 2-5%          | Depends on intent match     |

### Engagement Time

| Page Type         | Healthy Range | Low (flag) |
| ----------------- | ------------- | ---------- |
| Blog post         | 30-90s        | < 15s      |
| Product/trip page | 40-120s       | < 20s      |
| Homepage          | 20-60s        | < 10s      |
| Contact page      | 15-40s        | < 8s       |
| Checkout          | 60-180s       | < 20s      |

### Mobile vs Desktop

| Metric           | Mobile typical | Desktop typical |
| ---------------- | -------------- | --------------- |
| Bounce rate      | 55-70%         | 40-55%          |
| Form completion  | 10-20% lower   | baseline        |
| Engagement time  | 15-30% lower   | baseline        |
| Conversion rate  | 30-50% lower   | baseline        |

## GA4 File Patterns

| Pattern                   | Contains    |
| ------------------------- | ----------- |
| `*Landing_page*.csv`      | Entry pages |
| `*Pages_and_screens*.csv` | All pages   |
| `*Events*.csv`            | User events |

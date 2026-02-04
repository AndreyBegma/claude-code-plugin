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

## GA4 File Patterns

| Pattern                   | Contains    |
| ------------------------- | ----------- |
| `*Landing_page*.csv`      | Entry pages |
| `*Pages_and_screens*.csv` | All pages   |
| `*Events*.csv`            | User events |

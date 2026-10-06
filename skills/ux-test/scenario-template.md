# Scenario Template

Use this as a starting point for creating UX test scenarios. Save your scenarios as `{N}-{name}.md` files in `{project_root}/.claude/ux-tests/` (e.g., `1-login-flow.md`, `2-checkout.md`).

Generate scenarios automatically with `/cs-ux-scenario` or create them manually.

---

# Login Flow

## Config
- url: http://localhost:3000/login
- viewport: 1440x900
- mobile: 375x812

## Steps

### 1. Open login page
- Action: Navigate to /login
- Expected: Login form is visible with email and password fields

### 2. Enter credentials
- Action: Type "user@example.com" into email field, "password123" into password field
- Expected: Fields are filled, no validation errors shown

### 3. Submit form
- Action: Click "Sign In" button
- Expected: Redirect to /dashboard within 3 seconds

### 4. Verify dashboard
- Action: Wait for page load
- Expected: Welcome message visible, navigation menu loaded

## Checkpoints
- [ ] Form has proper labels for screen readers
- [ ] Loading indicator shown during authentication
- [ ] Error state handles wrong credentials gracefully
- [ ] Tab order is logical (email → password → submit)
- [ ] Password field masks input
- [ ] Focus returns to email field after failed login attempt

---

## Format Reference

### Config Section

| Field      | Required | Default    | Description                                            |
| ---------- | -------- | ---------- | ------------------------------------------------------ |
| `url`      | Yes      | —          | Starting URL for the scenario                          |
| `viewport` | No       | 1440x900   | Desktop viewport size                                  |
| `mobile`   | No       | 375x812    | Mobile viewport size. Set `skip` to skip mobile pass   |

### Step Format

```markdown
### {number}. {Short description}
- Action: {what to do — see action types below}
- Expected: {what should happen after the action}
```

### Action Types

| Action                                | Example                                           |
| ------------------------------------- | ------------------------------------------------- |
| `Navigate to {path}`                  | Navigate to /settings                             |
| `Type "{text}" into {field}`          | Type "John" into first name field                 |
| `Click "{text}"`                      | Click "Save Changes" button                       |
| `Wait for {condition}`                | Wait for success notification                     |
| `Scroll to {target}`                  | Scroll to "Billing" section                       |
| `Select "{value}" from {dropdown}`    | Select "Monthly" from billing cycle dropdown      |
| `Press {key}`                         | Press Tab                                         |
| `Hover over {element}`               | Hover over profile menu                           |
| `Clear {field}`                       | Clear search input                                |

### Checkpoints

Checkpoints are quality checks verified after all steps complete. Use checkbox format:

```markdown
## Checkpoints
- [ ] Descriptive checkpoint item
- [ ] Another quality check
```

Common checkpoint categories:
- **Accessibility**: labels, focus order, keyboard navigation, screen reader support
- **Loading UX**: indicators, skeleton screens, button states during submit
- **Error handling**: validation messages, network error recovery, empty states
- **Design consistency**: spacing, color usage, typography hierarchy
- **Responsive**: mobile layout, touch targets, viewport adaptation
- **Performance**: page load time, interaction responsiveness

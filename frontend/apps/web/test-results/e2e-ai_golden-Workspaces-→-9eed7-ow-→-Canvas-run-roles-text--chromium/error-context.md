# Page snapshot

```yaml
- generic [ref=e1]:
  - generic [ref=e2]:
    - complementary [ref=e3]:
      - generic [ref=e4]:
        - generic [ref=e5]: Navigation
        - navigation [ref=e6]:
          - link "Canvas" [ref=e7] [cursor=pointer]:
            - /url: /canvas
          - link "Workspaces" [ref=e8] [cursor=pointer]:
            - /url: /workspaces
    - generic [ref=e9]:
      - generic [ref=e11]:
        - link "iceOS Studio" [ref=e12] [cursor=pointer]:
          - /url: /
        - generic [ref=e13]:
          - combobox "Workspace" [ref=e14]:
            - option "Workspace" [selected]
          - combobox "Project" [ref=e15]:
            - option "Project" [selected]
          - button "New" [ref=e16] [cursor=pointer]
      - main [ref=e17]:
        - generic [ref=e18]:
          - generic [ref=e19]:
            - generic [ref=e20]: Workspaces
            - button "New Workspace" [active] [ref=e21] [cursor=pointer]
          - generic [ref=e23]: No workspaces yet. Click "New Workspace" to get started.
  - region "Notifications (F8)":
    - list
  - alert [ref=e24]
```

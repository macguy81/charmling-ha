# Brand images

Home Assistant and HACS take an integration's icon and logo from the
[home-assistant/brands](https://github.com/home-assistant/brands) repository,
not from the integration itself. These are the files to submit there, under
`custom_integrations/charmling/`: the app icon at 256 and 512, and the
wordmark (the mask beside "Charmling", in ink for light themes and cream
for dark) at 256 and 512 high.

```bash
gh repo fork home-assistant/brands --clone -- --depth 1
cd brands
mkdir -p custom_integrations/charmling
cp ~/Charmling/charmling-ha/brands/custom_integrations/charmling/*.png custom_integrations/charmling/
git checkout -b charmling
git add custom_integrations/charmling && git commit -m "Add Charmling (custom integration)"
git push -u origin charmling
gh pr create --title "Add Charmling (custom integration)" \
  --body "Brand images for the Charmling custom integration: https://github.com/macguy81/charmling-ha"
```

Once merged, remove `brands` from the HACS action's `ignore` list in
`.github/workflows/validate.yml`.

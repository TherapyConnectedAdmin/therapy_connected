# S3 CORS Configuration for Intro Video Playback

To allow localhost development and production domains to load videos directly from the S3 bucket without CORS errors, apply a CORS configuration to the bucket (AWS Console > S3 > Bucket > Permissions > CORS configuration):

```json
[
  {
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["GET", "HEAD"],
    "AllowedOrigins": [
      "http://localhost:8000",
      "https://therapyconnected.com",
      "https://www.therapyconnected.com"
    ],
    "ExposeHeaders": ["Accept-Ranges","Content-Length","Content-Range"],
    "MaxAgeSeconds": 3000
  }
]
```

Notes:
- Include only the domains you actually serve from (add staging domains as needed).
- HEAD is required for the lightweight probe; GET for actual playback.
- Expose optional headers if you later implement byte-range analytics or custom logic.
- If you use CloudFront in front of S3, update the distribution behavior to forward Origin headers (or use an Origin Access Identity and place CORS on the distribution instead).

## Troubleshooting
| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| 200 response but browser console shows CORS error and video fails | Missing domain in AllowedOrigins | Add origin and re-save CORS; invalidate CDN if fronted by CloudFront |
| Video loads but HEAD probe logs warning | no-cors mode hides status; this is expected and safe | None; element playback governs user experience |
| 403 Forbidden on video URL | Object ACL / bucket policy mismatch | Ensure bucket policy allows s3:GetObject for public or signed delivery |

After updating, wait a few minutes and hard refresh (Shift+Reload) in the browser.

# Asset Structure — placement & loading principles

Quy tắc đặt asset (art 2D, 3D model, content per-entity, audio, third-party). Cây thư mục
CỤ THỂ là per-project (host rules define); file này giữ INVARIANT.

## Vùng asset (zone-based layout)

Project chia asset thành các VÙNG có chủ, mỗi vùng có load mechanism rõ:

| Vùng | Chứa gì | Load |
|---|---|---|
| UI chrome | asset UI share ≥2 screen + per-screen art | UXML/USS reference trực tiếp |
| Content per-entity | art + prefab + asset chain của MỘT entity (hero/item…) | GUID dependency, load qua hub + facade |
| Audio | music/SFX clip | theo cơ chế project (direct ref hoặc addressables) |
| Third-party | pack Asset Store / vendor, giữ nguyên cấu trúc nội bộ | GUID reference |
| Misc | asset lẻ dùng chung không thuộc vùng nào | GUID reference |
| Staging (`_Temp`) | asset chưa phân loại (raw AI-gen, test art) | KHÔNG reference từ runtime |

- Art share ≥2 screen → đưa lên vùng common, không copy vào từng screen.
- Unity-generated folders (TextMesh Pro, UI Toolkit themes, AddressableAssetsData,
  StreamingAssets…) giữ tại root — không di chuyển.

## Content per-entity — keyed by config id

- Content của một entity gom per-id: `<contentRoot>/<Entities>/<configId>/` — id nằm ở
  folder, tên file bên trong ngắn gọn theo chức năng (kebab-case cho art 2D).
- Asset **chỉ 1 entity dùng** mà prefab của entity reference (trực tiếp hoặc qua chain) gom
  vào bucket type dưới folder id đó. Asset **dùng chung ≥2 entity** giữ vị trí shared —
  không copy vào từng id. Script `.cs` giữ nguyên — generic, không gom.
- File trong bucket 3D (Model/Material/Texture/Animation/…) GIỮ nguyên tên source-pack —
  là GUID dependency của prefab, naming convention không áp cho nhóm này.
- Collision (nhiều nguồn khác GUID cùng tên file cùng bucket): tách bằng subfolder đặt theo
  path nguồn.

## Loading — facade, không path-load

- Code KHÔNG gọi `Resources.Load` / `Addressables.LoadAssetAsync` trực tiếp rải rác cho
  content asset — đi qua MỘT facade per-domain (preload batch async, `Get*` chỉ đọc cache,
  miss log một lần, release có chủ).
- Reference giữa asset đi theo GUID (serialized ref), không path string — move/rename không
  vỡ runtime.
- CARVE-OUT: editor-only maintenance tool (menu `Tools/*`, folder `Editor/`) ĐƯỢC hardcode
  path folder dạng string cho `AssetDatabase` folder-scan — không phải runtime asset load.

## Third-party packs

- Toàn bộ pack đặt dưới MỘT folder third-party của project, giữ nguyên tên + cấu trúc nội bộ
  từng pack (không rename/tách file bên trong).
- Update pack: import về path gốc → move nguyên khối vào folder third-party bằng
  `AssetDatabase.MoveAsset` / kéo trong editor (không mv ngoài filesystem khi editor mở).
- Code/UXML không reference asset trong pack theo path string — chỉ GUID.

## Addressables (nếu dùng)

Group `AG_<Feature>`, label kebab-case lowercase, address `<feature>/<name>` lowercase
([conventions.md](conventions.md#addressables)).

## Naming asset

Theo [conventions.md](conventions.md#unity-assets): `Tex_<Target>_<Channel>`,
`Mat_<Target>_<Variant>`, `SO_<Domain>_<Name>`. VisualElement `name` + USS class:
[naming-ui-toolkit.md](naming-ui-toolkit.md).

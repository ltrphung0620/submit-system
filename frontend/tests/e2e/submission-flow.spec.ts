import { expect, test } from "@playwright/test";

const pngBase64 =
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=";

test("public API, realtime grouping, CRUD, image, history CSV and mobile flow", async ({
  page,
  request,
}) => {
  const suffix = Date.now();
  const kisFile = `synthetic-e2e-${suffix}-kis`;
  const qaFile = `synthetic-e2e-${suffix}-qa`;
  const trakeFile = `synthetic-e2e-${suffix}-trake`;
  const consoleErrors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });

  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: /API nhận bài/ }),
  ).toBeVisible();
  await expect(page.getByText("Official format: chưa xác minh")).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Xuất chính thức" }),
  ).toHaveCount(0);

  const kis = await request.post("/api/v1/submissions", {
    data: {
      file_name: kisFile,
      img_id: 24834,
      video_id: "L21_V001",
      submitter: "Định",
      image_base64: pngBase64,
      image_mime_type: "image/png",
    },
  });
  expect(kis.status()).toBe(201);
  const second = await request.post("/api/v1/submissions", {
    data: {
      file_name: kisFile,
      img_id: 24835,
      video_id: "L21_V001",
      submitter: "Member 2",
    },
  });
  expect(second.status()).toBe(201);
  expect(
    (
      await request.post("/api/v1/submissions", {
        data: {
          file_name: qaFile,
          img_id: 24834,
          video_id: "L21_V001",
          answer: "Bình Định",
          submitter: "Định",
        },
      })
    ).status(),
  ).toBe(201);
  expect(
    (
      await request.post("/api/v1/submissions", {
        data: {
          file_name: trakeFile,
          img_id: [24834, 25230, 25432],
          video_id: "L21_V001",
          submitter: "Định",
        },
      })
    ).status(),
  ).toBe(201);

  const kisCard = page.locator(".query-card").filter({ hasText: kisFile });
  await expect(kisCard.getByText("Đến #1")).toBeVisible({ timeout: 2_000 });
  await expect(kisCard.getByText("Đến #2")).toBeVisible();
  await kisCard.getByRole("button", { name: "Sửa" }).first().click();
  await page.getByLabel("Frame", { exact: true }).fill("20000");
  await page.getByRole("button", { name: "Lưu candidate" }).click();
  await expect(kisCard.getByText("Frame 20000")).toBeVisible();
  await expect(kisCard.getByText("Đến #1")).toBeVisible();

  page.once("dialog", (dialog) => dialog.accept());
  await kisCard.getByRole("button", { name: "Xóa" }).last().click();
  await expect(kisCard.getByText("Đến #2")).not.toBeVisible();

  await kisCard.getByRole("button", { name: "Mở ảnh kiểm tra" }).click();
  await expect(
    page.getByRole("dialog", { name: "Ảnh kiểm tra" }),
  ).toBeVisible();
  await page
    .getByRole("dialog", { name: "Ảnh kiểm tra" })
    .getByRole("button", { name: "Đóng" })
    .click();

  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Xuất lịch sử CSV" }).click();
  const download = await downloadPromise;
  const csvBytes = await (
    await import("node:fs/promises")
  ).readFile(await download.path());
  const csvText = csvBytes.toString("utf8");
  expect(csvText).toContain(
    "received_at,file_name,query_type,arrival_seq,video_id,img_id,answer,submitter",
  );
  expect(csvText).toContain("Bình Định");

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: /API nhận bài/ }),
  ).toBeVisible();
  await expect(page.locator(".query-card").first()).toBeVisible();
  expect(consoleErrors).toEqual([]);
});

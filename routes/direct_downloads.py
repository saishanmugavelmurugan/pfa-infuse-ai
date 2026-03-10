"""
Direct Download Endpoints for Marketing Assets
Forces browser to download files instead of displaying them
"""

from fastapi import APIRouter
from fastapi.responses import FileResponse, Response
import httpx
import os

router = APIRouter(prefix="/direct-download", tags=["downloads"])

# Base paths
DOWNLOADS_DIR = "/app/frontend/public/downloads"

@router.get("/video")
async def download_video():
    """Download promotional video with forced download"""
    file_path = f"{DOWNLOADS_DIR}/HealthTrackPro_Promo_Video.mp4"
    if os.path.exists(file_path):
        return FileResponse(
            path=file_path,
            filename="HealthTrackPro_Promo_Video.mp4",
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": "attachment; filename=HealthTrackPro_Promo_Video.mp4"
            }
        )
    return {"error": "Video not found"}


@router.get("/full-video")
async def download_full_video():
    """Download full promotional video with forced download"""
    file_path = f"{DOWNLOADS_DIR}/HealthTrackPro_Full_Promo_Video.mp4"
    if os.path.exists(file_path):
        return FileResponse(
            path=file_path,
            filename="HealthTrackPro_Full_Promo_Video.mp4",
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": "attachment; filename=HealthTrackPro_Full_Promo_Video.mp4"
            }
        )
    return {"error": "Full video not found"}


@router.get("/marketing-pdf")
async def download_marketing_pdf():
    """Download marketing PDF with forced download"""
    file_path = f"{DOWNLOADS_DIR}/HealthTrack_Pro_Marketing_Campaigns_Pricing_2026.pdf"
    if os.path.exists(file_path):
        return FileResponse(
            path=file_path,
            filename="HealthTrack_Pro_Marketing_Campaigns_Pricing_2026.pdf",
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": "attachment; filename=HealthTrack_Pro_Marketing_Campaigns_Pricing_2026.pdf"
            }
        )
    return {"error": "PDF not found"}


@router.get("/compliance-pdf")
async def download_compliance_pdf():
    """Download compliance PDF with forced download"""
    file_path = f"{DOWNLOADS_DIR}/Infuse_HealthTrack_Pro_Compliance_2026.pdf"
    if os.path.exists(file_path):
        return FileResponse(
            path=file_path,
            filename="Infuse_HealthTrack_Pro_Compliance_2026.pdf",
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": "attachment; filename=Infuse_HealthTrack_Pro_Compliance_2026.pdf"
            }
        )
    return {"error": "PDF not found"}


@router.get("/dha-compliance")
async def download_dha_compliance():
    """Download DHA Compliance Assessment PDF"""
    file_path = f"{DOWNLOADS_DIR}/DHA_Compliance_Assessment_2026.pdf"
    if os.path.exists(file_path):
        return FileResponse(
            path=file_path,
            filename="DHA_Compliance_Assessment_2026.pdf",
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": "attachment; filename=DHA_Compliance_Assessment_2026.pdf"
            }
        )
    return {"error": "PDF not found"}


@router.get("/dha-architecture")
async def download_dha_architecture():
    """Download DHA Technical Architecture PDF"""
    file_path = f"{DOWNLOADS_DIR}/DHA_Technical_Architecture_2026.pdf"
    if os.path.exists(file_path):
        return FileResponse(
            path=file_path,
            filename="DHA_Technical_Architecture_2026.pdf",
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": "attachment; filename=DHA_Technical_Architecture_2026.pdf"
            }
        )
    return {"error": "PDF not found"}


@router.get("/dha-pitch")
async def download_dha_pitch():
    """Download DHA Partnership Pitch PDF"""
    file_path = f"{DOWNLOADS_DIR}/DHA_Partnership_Pitch_2026.pdf"
    if os.path.exists(file_path):
        return FileResponse(
            path=file_path,
            filename="DHA_Partnership_Pitch_2026.pdf",
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": "attachment; filename=DHA_Partnership_Pitch_2026.pdf"
            }
        )
    return {"error": "PDF not found"}


@router.get("/image/{image_name}")
async def download_image(image_name: str):
    """Download campaign images with forced download"""
    image_urls = {
        "whatsapp": "https://static.prod-images.emergentagent.com/jobs/8ec6f9ed-4ccd-47ea-80b6-b4d6b3c66127/images/246e09e8dc415c90592727780d26c27f178431fd7770d80e4f0f5c420f134638.png",
        "facebook": "https://static.prod-images.emergentagent.com/jobs/8ec6f9ed-4ccd-47ea-80b6-b4d6b3c66127/images/fbe513f570b2a92716abd6f49925aa29beaac02a84f992357970d528d85558c8.png",
        "linkedin": "https://static.prod-images.emergentagent.com/jobs/8ec6f9ed-4ccd-47ea-80b6-b4d6b3c66127/images/4632ab9071c4331316330ad0db00b60e4ce1dcf9658efa92994e6d633fdc6a29.png",
        "instagram": "https://static.prod-images.emergentagent.com/jobs/8ec6f9ed-4ccd-47ea-80b6-b4d6b3c66127/images/0e030eece050da74d40c6bc363f40c790c88131befc01e729f4b9e37df8d2c0a.png",
        "hero": "https://static.prod-images.emergentagent.com/jobs/8ec6f9ed-4ccd-47ea-80b6-b4d6b3c66127/images/2cfc2f380f79b1b11282563bdeebc8e5b66a591f2ab912e7133d939710797d89.png"
    }
    
    if image_name not in image_urls:
        return {"error": "Image not found"}
    
    async with httpx.AsyncClient() as client:
        response = await client.get(image_urls[image_name])
        if response.status_code == 200:
            return Response(
                content=response.content,
                media_type="application/octet-stream",
                headers={
                    "Content-Disposition": f"attachment; filename=HealthTrackPro_{image_name.title()}_Campaign.png"
                }
            )
    
    return {"error": "Failed to fetch image"}

import asyncio
import logging
from archon_sdk.client import ArchonClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s - SOC_AGENT - [%(levelname)s] - %(message)s")
logger = logging.getLogger("soc_agent")

async def main():
    logger.info("Initializing SOC Autonomous Agent...")
    
    async with ArchonClient(base_url="http://localhost:8000") as archon:
        # Scenario 1: Low Risk (Auto-approved)
        logger.info("\n--- SCENARIO 1: LOW RISK ---")
        logger.info("Event: Detected routine port scan.")
        action1 = "Block source IP 192.168.1.100 at firewall."
        conf1 = 0.95
        
        logger.info(f"Proposing Action: '{action1}' with confidence: {conf1}")
        approved1 = await archon.execute(action=action1, confidence=conf1, threshold=0.90, user_id="soc_admin@company.com")
        if approved1:
            logger.info(f"Action '{action1}' EXECUTED successfully.")
        else:
            logger.warning(f"Action '{action1}' REJECTED.")
            
        await asyncio.sleep(2)
        
        # Scenario 2: High Risk (Requires Step-Up)
        logger.info("\n--- SCENARIO 2: HIGH RISK ---")
        logger.info("Event: Detected lateral movement in engineering subnet.")
        action2 = "Isolate engineering VLAN."
        conf2 = 0.75 # Lower than threshold (0.90)
        
        logger.info(f"Proposing Action: '{action2}' with confidence: {conf2}")
        
        # This will pause and wait for the Step-Up Auth URL to be clicked and approved
        approved2 = await archon.execute(action=action2, confidence=conf2, threshold=0.90, user_id="soc_admin@company.com")
        
        if approved2:
            logger.info(f"Action '{action2}' EXECUTED successfully.")
        else:
            logger.warning(f"Action '{action2}' FAILED/TIMEOUT.")
            
        await asyncio.sleep(2)
        
        # Scenario 3: Critical (Requires Quorum)
        logger.info("\n--- SCENARIO 3: CRITICAL RISK ---")
        logger.info("Event: Global ransomware signature detected on core DB.")
        action3 = "Wipe affected DB drives and failover to standby."
        
        logger.info(f"Proposing Action: '{action3}' requiring QUORUM.")
        trustees = ["ciso@company.com", "vp_eng@company.com", "oncall_lead@company.com"]
        
        # This will pause and wait for TWO Auth0 Step-up approval callbacks for the listed trustees
        approved3 = await archon.require_quorum(action=action3, trustees=trustees, required=2)
        
        if approved3:
            logger.info(f"Action '{action3}' EXECUTED successfully.")
        else:
            logger.warning(f"Action '{action3}' FAILED/TIMEOUT.")
            
    logger.info("SOC Agent simulation completed.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Terminated by user.")

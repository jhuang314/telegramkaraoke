import Head from "next/head";
import Image from "next/image";
import { Inter } from "next/font/google";
import { useState } from "react";
import styles from "@/styles/Home.module.css";
import Moment from "react-moment";
import {
  Address,
  ConnectButton,
  Connector,
  NFTCard,
  useNFT,
} from "@ant-design/web3";
import { getWeb3AssetUrl } from "@ant-design/web3-common";
import {
  MetaMask,
  WagmiWeb3ConfigProvider,
  Sepolia,
} from "@ant-design/web3-wagmi";
import { abi } from "./contract";
import {
  WagmiProvider,
  http,
  createConfig,
  useReadContract,
  useReadContracts,
} from "wagmi";

import { injected } from "wagmi/connectors";

import { Button, Flex, Modal, Spin } from "antd";

const inter = Inter({ subsets: ["latin"] });

import { mainnet, sepolia, opBNBTestnet } from "wagmi/chains";

const config = createConfig({
  chains: [opBNBTestnet],
  transports: {
    [opBNBTestnet.id]: http(),
  },
  connectors: [
    injected({
      target: "metaMask",
    }),
  ],
});

const contractAddress = "0xCB7b3F767D536b7F884f0342372D8dE6E577a1e2";

export default function Home() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <Head>
        <title>Telegram Karaoke Bot</title>
        <meta name="description" content="Telegram Karaoke Bot NFTs" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>
      <main className={styles.main}>
        <Flex
          gap="middle"
          justify="space-between"
          align="center"
          className={styles.header}
        >
          <h1>Telegram Karaoke</h1>

          <Button type="primary" size="large" onClick={() => setOpen(true)}>
            Play on Telegram!
          </Button>

          <Modal
            title="How to play"
            centered
            open={open}
            onOk={() => setOpen(false)}
            onCancel={() => setOpen(false)}
          >
            <h2>Start conversation with the bot:</h2>
            <img src="https://cdn.discordapp.com/attachments/807630293917761607/1323713788385558538/Screenshot_2024-12-31_130101-removebg-preview.png?ex=67758408&is=67743288&hm=1c8f76db9714ce1de8881dd8612e508b95a121ce247ae60c9b7e273fdc86cfbe&"></img>
            <h2>Use the /help command to start!</h2>
          </Modal>
        </Flex>

        <WagmiWeb3ConfigProvider config={config} wallets={[MetaMask()]}>
          <Content></Content>
        </WagmiWeb3ConfigProvider>
        <footer className={styles.footer}>
          Background Designed by <a href="www.freepik.com">Freepik</a>
        </footer>
      </main>
    </>
  );
}

function Content() {
  const result = useReadContract({
    address: contractAddress,
    abi: abi,
    functionName: "tokenCount",
  });

  const contractCalls = Array.from({ length: Number(result.data) }).map(
    (_, index) => ({
      abi: abi,
      address: contractAddress,
      functionName: "ownerOf",
      args: [index],
    }),
  );

  const { data: owners, isLoading: ownersLoading } = useReadContracts({
    contracts: contractCalls,
  });

  if (result.isLoading || ownersLoading) {
    return <Spin spinning fullscreen />;
  }

  if (result.error) {
    return <div>Error: {result.error.message}</div>;
  }

  const tokenCount = Number(result.data) - 1;

  return (
    <>
      <Flex wrap gap="middle" justify="space-evenly" align="center">
        {[...Array(tokenCount).keys()].reverse().map((i) => (
          <NFTContent
            key={i}
            tokenId={i + 1}
            tokenOwner={owners[i]}
          ></NFTContent>
        ))}
      </Flex>
    </>
  );
}

function NFTContent({
  tokenId,
  tokenOwner,
}: {
  tokenId: number;
  tokenOwner: { result: string; status: string };
}) {
  const { metadata, error, loading } = useNFT(contractAddress, tokenId);

  if (loading || metadata.attributes === undefined) return <></>;

  const attributes = metadata.attributes || [];

  let score = 0;
  let song = "";
  let time = "";
  for (let attr of attributes) {
    if (attr.trait_type === "Score") {
      score = Number(attr.value);
    } else if (attr.trait_type === "Song") {
      song = attr.value || "";
    } else if (attr.trait_type === "Timestamp") {
      time = attr.value || "";
    } else if ("score" in attr) {
      score = Number(attr.score);
    } else if ("song" in attr) {
      song = (attr.song as string) || "";
    } else if ("timestamp" in attr) {
      time = attr.timestamp as string;
    }
  }

  const description = (
    <div>
      <p>Score: {score}</p>
      <p>Song: {song}</p>
      <p>
        Time: <Moment parse="YYYYMMDDhhmmss">{time}</Moment>
      </p>
      <p>Token ID: {tokenId}</p>
    </div>
  );

  return (
    <NFTCard
      address={contractAddress}
      tokenId={tokenId}
      description={description}
      footer=<>
        <div>Owner:</div>
        <Address address={tokenOwner.result} copyable></Address>
      </>
    />
  );
}
